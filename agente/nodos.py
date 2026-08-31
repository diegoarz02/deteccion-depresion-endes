"""Nodos del grafo del agente.

Cada nodo recibe el estado, hace una cosa y devuelve el fragmento de estado que
cambia. Todos registran su paso en ``trazas``, de modo que una ejecución se
puede auditar entera después.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import time
from pathlib import Path

import guardrails
import prompts
import recursos
from estado import EstadoAgente

log = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parents[1]
TABLAS = RAIZ / "resultados" / "tablas"
MODELOS = RAIZ / "resultados" / "modelos"

DISCLAIMER = (
    "Esta herramienta estima riesgo epidemiológico con fines académicos y de salud "
    "pública. No constituye un diagnóstico médico ni reemplaza la evaluación de un "
    "profesional de salud mental."
)
LINEA_AYUDA = (
    "Si te sientes mal, busca ayuda profesional. En el Perú puedes llamar "
    "gratuitamente a la Línea 113, opción 5 (salud mental), del MINSA."
)

MAX_INTENTOS = 2


def _traza(estado: EstadoAgente, nodo: str, inicio: float, resumen: str) -> list[dict]:
    """Añade una entrada al registro de ejecución."""
    return [*estado.get("trazas", []),
            {"nodo": nodo, "duracion_ms": round((time.perf_counter() - inicio) * 1000, 1),
             "resumen": resumen}]


# ─────────────────────────────────────────────────────────────────────
# 1. Validación
# ─────────────────────────────────────────────────────────────────────


def validar_entrada(estado: EstadoAgente) -> dict:
    """Valida el perfil con los esquemas de la API.

    Reutilizar el mismo Pydantic que la API evita que el agente acepte perfiles
    que el servicio rechazaría.
    """
    inicio = time.perf_counter()
    perfil = estado.get("perfil")
    if not perfil:
        return {"veredicto_seguridad": "bloqueado",
                "motivo_rechazo": "No se recibió ningún perfil.",
                "trazas": _traza(estado, "validar_entrada", inicio, "sin perfil")}
    try:
        import sys
        sys.path.insert(0, str(RAIZ / "api"))
        from esquemas import Perfil

        Perfil(**perfil)
        return {"trazas": _traza(estado, "validar_entrada", inicio, "perfil válido")}
    except Exception as e:
        return {"veredicto_seguridad": "bloqueado",
                "motivo_rechazo": f"Perfil inválido: {e}",
                "trazas": _traza(estado, "validar_entrada", inicio, f"inválido: {str(e)[:90]}")}


# ─────────────────────────────────────────────────────────────────────
# 1b. Detección de crisis
# ─────────────────────────────────────────────────────────────────────


def detectar_crisis(estado: EstadoAgente) -> dict:
    """Comprueba si la consulta indica una situación de crisis.

    Corre **antes** de cualquier llamada al modelo de lenguaje, y es
    determinista a propósito. Si se activa, la respuesta no la redacta el LLM:
    se emite una plantilla fija y revisada.
    """
    inicio = time.perf_counter()
    r = recursos.detectar_crisis(
        perfil=estado.get("perfil"),
        prediccion=estado.get("prediccion"),
        texto=estado.get("entrada_usuario", ""))
    return {"hay_crisis": r["hay_crisis"], "motivos_crisis": r["motivos"],
            "trazas": _traza(estado, "detectar_crisis", inicio,
                             "CRISIS DETECTADA" if r["hay_crisis"] else "sin señales de crisis")}


def respuesta_crisis_fija(estado: EstadoAgente) -> dict:
    """Devuelve el texto de crisis, que no pasa por ningún modelo generativo."""
    inicio = time.perf_counter()
    texto, recs = recursos.respuesta_crisis()
    cuerpo = texto + "\n\n---\n\n" + recursos.formatear(recs)
    return {"borrador": cuerpo, "salida_final": cuerpo, "modo": "crisis",
            "recursos_ofrecidos": [r["id"] for r in recs],
            "trazas": _traza(estado, "respuesta_crisis_fija", inicio,
                             "plantilla fija, sin llamada al modelo")}


# ─────────────────────────────────────────────────────────────────────
# 2. Predicción
# ─────────────────────────────────────────────────────────────────────


def predecir(estado: EstadoAgente) -> dict:
    """Obtiene la predicción del modelo, si no venía ya dada."""
    inicio = time.perf_counter()
    if estado.get("prediccion"):
        return {"trazas": _traza(estado, "predecir", inicio, "predicción recibida")}
    try:
        import sys
        sys.path.insert(0, str(RAIZ / "api"))
        from esquemas import Perfil
        from servicio import servicio

        if not servicio.cargado:
            servicio.cargar()
        pred = servicio.predecir(Perfil(**estado["perfil"]))
        d = pred.model_dump(mode="json")
        return {"prediccion": d,
                "trazas": _traza(estado, "predecir", inicio,
                                 f"probabilidad {d['probabilidad_pct']:.1f} %")}
    except Exception as e:
        return {"veredicto_seguridad": "bloqueado",
                "motivo_rechazo": f"No se pudo predecir: {e}",
                "trazas": _traza(estado, "predecir", inicio, f"error: {str(e)[:90]}")}


# ─────────────────────────────────────────────────────────────────────
# 3. Recuperación de contexto
# ─────────────────────────────────────────────────────────────────────


def recuperar_contexto(estado: EstadoAgente) -> dict:
    """Recupera hallazgos del estudio pertinentes al perfil.

    Es un RAG ligero por palabras clave sobre los CSV de resultados. No se monta
    un vector store: con una decena de tablas conocidas, la búsqueda semántica
    añadiría una dependencia pesada sin mejorar la respuesta.
    """
    inicio = time.perf_counter()
    perfil = estado.get("perfil") or {}
    contexto: list[str] = []

    try:
        import pandas as pd

        prev = pd.read_csv(TABLAS / "tabla_08_prevalencias_ponderadas.csv")
        for campo, variable in [("sexo", "Sexo"), ("grupo_etario", "Grupo etario"),
                                ("region_natural", "Región natural")]:
            valor = perfil.get(campo)
            if not valor:
                continue
            fila = prev[(prev.variable == variable) & (prev.categoria == str(valor))]
            if len(fila):
                r = fila.iloc[0]
                contexto.append(
                    "En el grupo «{}» la prevalencia ponderada es del {} %.".format(
                        valor, f"{r.prevalencia:.1f}".replace(".", ",")))

        brecha = pd.read_csv(TABLAS / "tabla_11_brecha_atencion.csv")
        contexto.append(
            f"En el Perú, el {brecha.brecha.iloc[0]:.0f} % de las personas con "
            f"sintomatología depresiva moderada o grave no recibió atención "
            f"profesional en los últimos doce meses.")

        log_t = pd.read_csv(TABLAS / "tabla_22_logistica_diseno_complejo.csv")
        for termino, campo in [("alcohol_problematico", "consumo_problematico_alcohol"),
                               ("hta_dx", "hipertension"), ("diabetes_dx", "diabetes")]:
            if perfil.get(campo):
                fila = log_t[log_t.termino == termino]
                if len(fila):
                    r = fila.iloc[0]
                    contexto.append(
                        "En el modelo ajustado, ese factor se asocia con un odds ratio "
                        "de {} (IC 95 % {} – {}).".format(
                            f"{r['or']:.2f}".replace(".", ","),
                            f"{r.ic_inf:.2f}".replace(".", ","),
                            f"{r.ic_sup:.2f}".replace(".", ",")))
    except Exception as e:
        log.warning("No se pudo recuperar contexto: %s", e)

    return {"contexto_epidemiologico": contexto,
            "trazas": _traza(estado, "recuperar_contexto", inicio,
                             f"{len(contexto)} hallazgos")}


# ─────────────────────────────────────────────────────────────────────
# 4. Redacción
# ─────────────────────────────────────────────────────────────────────


def _hay_llm() -> bool:
    """Comprueba si hay clave de API y la librería instalada."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return False
    try:
        import langchain_anthropic  # noqa: F401
        return True
    except ImportError:
        return False


def redactar_interpretacion(estado: EstadoAgente) -> dict:
    """Redacta la interpretación con LLM o, si no hay, con plantillas.

    El modo degradado no es un mensaje de error: produce el mismo contenido
    sustantivo usando las cifras reales. El proyecto debe funcionar igual sin
    proveedor externo.
    """
    inicio = time.perf_counter()
    pred = estado["prediccion"]
    perfil = estado.get("perfil") or {}
    contexto = estado.get("contexto_epidemiologico", [])

    if not _hay_llm():
        texto = prompts.plantilla_determinista(pred, perfil, contexto)
        return {"borrador": texto, "modo": "degradado",
                "trazas": _traza(estado, "redactar_interpretacion", inicio,
                                 "modo degradado: sin clave de API")}
    try:
        from langchain_anthropic import ChatAnthropic

        llm = ChatAnthropic(model="claude-sonnet-5", temperature=0.3, max_tokens=600)
        mensaje = prompts.USUARIO.format(
            perfil=json.dumps(perfil, ensure_ascii=False, indent=2),
            probabilidad=pred["probabilidad_pct"],
            prevalencia=pred["prevalencia_nacional"] * 100,
            razon=pred["razon_sobre_prevalencia"],
            categoria=pred["categoria_riesgo"],
            factores=", ".join(f["factor"] for f in pred.get("factores_contribuyentes", []))
                     or "ninguno destacable",
            contexto="\n".join(f"- {c}" for c in contexto) or "- Sin contexto adicional.",
        )
        r = llm.invoke([("system", prompts.SISTEMA), ("human", mensaje)])
        return {"borrador": r.content.strip(), "modo": "llm",
                "trazas": _traza(estado, "redactar_interpretacion", inicio, "redactado con LLM")}
    except Exception as e:
        log.warning("El LLM falló, se pasa a modo degradado: %s", e)
        texto = prompts.plantilla_determinista(pred, perfil, contexto)
        return {"borrador": texto, "modo": "degradado",
                "trazas": _traza(estado, "redactar_interpretacion", inicio,
                                 f"degradado tras fallo del LLM: {str(e)[:70]}")}


# ─────────────────────────────────────────────────────────────────────
# 5. Guardrail
# ─────────────────────────────────────────────────────────────────────


def verificar_seguridad(estado: EstadoAgente) -> dict:
    """Somete el borrador al control de seguridad clínica."""
    inicio = time.perf_counter()
    r = guardrails.verificar(estado.get("borrador", ""))
    return {"veredicto_seguridad": r["veredicto"], "motivo_rechazo": r["motivo"],
            "trazas": _traza(estado, "verificar_seguridad", inicio,
                             f"{r['veredicto']}"
                             + (f" — {len(r['coincidencias'])} coincidencias"
                                if r["coincidencias"] else ""))}


def reescribir(estado: EstadoAgente) -> dict:
    """Corrige el borrador según el motivo del rechazo.

    Con LLM se pide la corrección; sin él, se vuelve a la plantilla determinista,
    que por construcción pasa el guardrail.
    """
    inicio = time.perf_counter()
    intentos = estado.get("intentos", 0) + 1
    motivo = estado.get("motivo_rechazo", "")

    if estado.get("modo") == "llm" and _hay_llm():
        try:
            from langchain_anthropic import ChatAnthropic

            llm = ChatAnthropic(model="claude-sonnet-5", temperature=0.2, max_tokens=600)
            r = llm.invoke([
                ("system", prompts.SISTEMA),
                ("human", f"Texto anterior:\n{estado['borrador']}\n\n"
                          + prompts.REESCRITURA.format(motivo=motivo)),
            ])
            return {"borrador": r.content.strip(), "intentos": intentos,
                    "trazas": _traza(estado, "reescribir", inicio,
                                     f"intento {intentos} con LLM")}
        except Exception as e:
            log.warning("Falló la reescritura con LLM: %s", e)

    texto = prompts.plantilla_determinista(
        estado["prediccion"], estado.get("perfil") or {},
        estado.get("contexto_epidemiologico", []))
    return {"borrador": texto, "intentos": intentos, "modo": "degradado",
            "trazas": _traza(estado, "reescribir", inicio,
                             f"intento {intentos} con plantilla determinista")}


# ─────────────────────────────────────────────────────────────────────
# 6. Salida
# ─────────────────────────────────────────────────────────────────────


def seleccionar_recursos(estado: EstadoAgente) -> dict:
    """Elige los recursos de ayuda del catálogo según el perfil.

    El modelo no interviene aquí: solo se consultan identificadores del catálogo
    verificado y el código sustituye cada uno por su dato real.
    """
    inicio = time.perf_counter()
    perfil = estado.get("perfil") or {}
    situaciones = ["sintomas_depresivos"]
    if perfil.get("violencia_pareja") or perfil.get("violencia_fisica"):
        situaciones.append("violencia_pareja")
    pred = estado.get("prediccion") or {}
    if pred.get("categoria_riesgo") == "alto":
        situaciones.append("seguimiento")
    recs = recursos.seleccionar(situaciones)
    return {"recursos_ofrecidos": [r["id"] for r in recs],
            "recursos_texto": recursos.formatear(recs),
            "trazas": _traza(estado, "seleccionar_recursos", inicio,
                             f"{len(recs)} recursos del catálogo")}


def formatear_salida(estado: EstadoAgente) -> dict:
    """Añade disclaimer, línea de ayuda, fuentes y nivel de incertidumbre."""
    inicio = time.perf_counter()
    # El AUC solo enriquece el cierre: si el archivo no está, se omite.
    auc = None
    with contextlib.suppress(Exception):
        auc = json.loads((MODELOS / "coeficientes_logistico.json")
                         .read_text(encoding="utf-8")).get("auc")
    final = estado["borrador"]
    if estado.get("recursos_texto"):
        final += "\n\n**Dónde encontrar ayuda**\n\n" + estado["recursos_texto"]
    final += prompts.cierre(DISCLAIMER, LINEA_AYUDA, estado.get("modo", "degradado"), auc)
    return {"salida_final": final,
            "trazas": _traza(estado, "formatear_salida", inicio,
                             f"{len(final)} caracteres")}


def manejar_error(estado: EstadoAgente) -> dict:
    """Produce una salida segura cuando algo falla o el guardrail bloquea.

    Nunca devuelve una traza técnica al usuario: devuelve un texto útil y
    orientado a buscar ayuda.
    """
    inicio = time.perf_counter()
    motivo = estado.get("motivo_rechazo", "Error no especificado")
    pred = estado.get("prediccion")

    if pred:
        texto = (
            f"De cada cien personas con este perfil, alrededor de "
            f"{pred['probabilidad_pct']:.0f} presentarían sintomatología depresiva "
            f"moderada o grave, frente al {pred['prevalencia_nacional'] * 100:.1f} % de "
            f"la población peruana de 15 años a más. Es una estimación epidemiológica "
            f"poblacional.")
    else:
        texto = ("No fue posible generar una estimación para los datos proporcionados. "
                 "Revisa que el perfil esté completo y dentro de los rangos válidos.")

    final = texto + prompts.cierre(DISCLAIMER, LINEA_AYUDA, "degradado")
    return {"salida_final": final, "modo": "degradado",
            "trazas": _traza(estado, "manejar_error", inicio, f"motivo: {motivo[:90]}")}


# ─────────────────────────────────────────────────────────────────────
# Aristas condicionales
# ─────────────────────────────────────────────────────────────────────


def ruta_tras_validar(estado: EstadoAgente) -> str:
    """Decide si continuar o abortar tras la validación."""
    return ("manejar_error" if estado.get("veredicto_seguridad") == "bloqueado"
            else "detectar_crisis")


def ruta_tras_crisis(estado: EstadoAgente) -> str:
    """Desvía a la plantilla fija si hay crisis; si no, sigue el flujo normal."""
    return "respuesta_crisis_fija" if estado.get("hay_crisis") else "predecir"


def ruta_tras_predecir(estado: EstadoAgente) -> str:
    """Decide si continuar o abortar tras la predicción."""
    return ("manejar_error" if estado.get("veredicto_seguridad") == "bloqueado"
            else "recuperar_contexto")


def ruta_tras_seguridad(estado: EstadoAgente) -> str:
    """Encamina según el veredicto del guardrail, con tope de reescrituras."""
    v = estado.get("veredicto_seguridad")
    if v == "aprobado":
        return "seleccionar_recursos"
    if v == "bloqueado":
        return "manejar_error"
    if estado.get("intentos", 0) >= MAX_INTENTOS:
        return "manejar_error"
    return "reescribir"
