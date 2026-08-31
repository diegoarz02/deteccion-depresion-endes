"""Construcción y ejecución del grafo del agente.

Flujo::

    START
      └─> validar_entrada
            ├─[inválido]────────────────────────> manejar_error ──> END
            └─[válido]──> predecir
                            ├─[error]───────────> manejar_error ──> END
                            └─> recuperar_contexto ──> redactar_interpretacion
                                                              │
                                                              v
                                                     verificar_seguridad
                                          ┌───────────────────┼───────────────┐
                                    [aprobado]          [reescribir]     [bloqueado]
                                          │                   │               │
                                          v                   v               v
                                  formatear_salida       reescribir     manejar_error
                                          │                   │               │
                                          │                   └──> verificar_seguridad
                                          │                        (máx. 2 intentos)
                                          v                                   v
                                         END                                 END

Uso
---
    python agente/grafo.py            # ejecuta la demostración
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(RAIZ / "api"))

import nodos  # noqa: E402
from estado import EstadoAgente  # noqa: E402

log = logging.getLogger(__name__)


def construir_grafo(con_memoria: bool = False):
    """Construye y compila el grafo de LangGraph.

    Parameters
    ----------
    con_memoria : bool, default False
        Si se añade un checkpointer en memoria para conservar el hilo de
        conversación entre llamadas.

    Returns
    -------
    CompiledStateGraph
    """
    from langgraph.graph import END, START, StateGraph

    g = StateGraph(EstadoAgente)

    g.add_node("validar_entrada", nodos.validar_entrada)
    g.add_node("detectar_crisis", nodos.detectar_crisis)
    g.add_node("respuesta_crisis_fija", nodos.respuesta_crisis_fija)
    g.add_node("predecir", nodos.predecir)
    g.add_node("recuperar_contexto", nodos.recuperar_contexto)
    g.add_node("redactar_interpretacion", nodos.redactar_interpretacion)
    g.add_node("verificar_seguridad", nodos.verificar_seguridad)
    g.add_node("reescribir", nodos.reescribir)
    g.add_node("seleccionar_recursos", nodos.seleccionar_recursos)
    g.add_node("formatear_salida", nodos.formatear_salida)
    g.add_node("manejar_error", nodos.manejar_error)

    g.add_edge(START, "validar_entrada")
    g.add_conditional_edges("validar_entrada", nodos.ruta_tras_validar,
                            {"detectar_crisis": "detectar_crisis",
                             "manejar_error": "manejar_error"})
    # La crisis se detecta ANTES de cualquier llamada al modelo y desvía a una
    # plantilla fija. Es determinista a propósito.
    g.add_conditional_edges("detectar_crisis", nodos.ruta_tras_crisis,
                            {"respuesta_crisis_fija": "respuesta_crisis_fija",
                             "predecir": "predecir"})
    g.add_edge("respuesta_crisis_fija", END)
    g.add_conditional_edges("predecir", nodos.ruta_tras_predecir,
                            {"recuperar_contexto": "recuperar_contexto",
                             "manejar_error": "manejar_error"})
    g.add_edge("recuperar_contexto", "redactar_interpretacion")
    g.add_edge("redactar_interpretacion", "verificar_seguridad")
    g.add_conditional_edges("verificar_seguridad", nodos.ruta_tras_seguridad,
                            {"seleccionar_recursos": "seleccionar_recursos",
                             "reescribir": "reescribir",
                             "manejar_error": "manejar_error"})
    g.add_edge("seleccionar_recursos", "formatear_salida")
    # El bucle de reescritura vuelve al guardrail; el tope de intentos lo corta.
    g.add_edge("reescribir", "verificar_seguridad")
    g.add_edge("formatear_salida", END)
    g.add_edge("manejar_error", END)

    if con_memoria:
        from langgraph.checkpoint.memory import MemorySaver
        return g.compile(checkpointer=MemorySaver())
    return g.compile()


_GRAFO = None


def obtener_grafo():
    """Devuelve el grafo compilado, construyéndolo solo la primera vez."""
    global _GRAFO
    if _GRAFO is None:
        _GRAFO = construir_grafo()
    return _GRAFO


def interpretar_perfil(perfil: dict, prediccion: dict | None = None,
                       entrada: str = "") -> dict:
    """Ejecuta el grafo sobre un perfil y devuelve la interpretación.

    Parameters
    ----------
    perfil : dict
        Perfil de la persona, con las claves que espera el esquema de la API.
    prediccion : dict, optional
        Predicción ya calculada. Si no se pasa, el agente la calcula.
    entrada : str, optional
        Consulta libre del usuario.

    Returns
    -------
    dict
        ``texto``, ``modo``, ``prediccion`` y ``trazas``.
    """
    estado: EstadoAgente = {
        "entrada_usuario": entrada, "perfil": perfil, "prediccion": prediccion,
        "contexto_epidemiologico": [], "borrador": None,
        "veredicto_seguridad": None, "motivo_rechazo": None,
        "intentos": 0, "modo": "degradado", "salida_final": None, "trazas": [],
        "hay_crisis": False, "motivos_crisis": [], "recursos_ofrecidos": [],
        "recursos_texto": "",
    }
    final = obtener_grafo().invoke(estado)
    return {
        "texto": final.get("salida_final", ""),
        "modo": final.get("modo", "degradado"),
        "prediccion": final.get("prediccion"),
        "hay_crisis": final.get("hay_crisis", False),
        "recursos": final.get("recursos_ofrecidos", []),
        # Se expone el identificador, no el texto: así se puede auditar qué
        # frase se mostró sin tener que buscarla dentro del cuerpo.
        "frase_animo": final.get("frase_animo"),
        "trazas": final.get("trazas", []),
    }


def exportar_diagrama() -> Path | None:
    """Exporta el diagrama del grafo a ``docs/grafo_agente.png``.

    Si no hay conexión para renderizar el PNG, guarda el Mermaid en texto, que
    es igual de reproducible y no depende de un servicio externo.
    """
    destino = RAIZ / "docs" / "grafo_agente.png"
    destino.parent.mkdir(parents=True, exist_ok=True)
    g = obtener_grafo().get_graph()
    try:
        destino.write_bytes(g.draw_mermaid_png())
        return destino
    except Exception as e:
        log.warning("No se pudo renderizar el PNG del grafo: %s", e)
        alterno = RAIZ / "docs" / "grafo_agente.mmd"
        alterno.write_text(g.draw_mermaid(), encoding="utf-8")
        return alterno


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    casos = [
        ("Perfil de riesgo bajo", {
            "sexo": "Hombre", "grupo_etario": "30-39", "nivel_educativo": "Superior",
            "region_natural": "Costa", "area": "Urbano", "edad": 35}),
        ("Perfil de riesgo alto", {
            "sexo": "Mujer", "grupo_etario": "60+", "nivel_educativo": "Primaria o menos",
            "region_natural": "Sierra", "area": "Rural", "edad": 68,
            "consumo_problematico_alcohol": True, "hipertension": True, "diabetes": True}),
        ("Perfil con señal de crisis (ítem sensible elevado)", {
            "sexo": "Mujer", "grupo_etario": "20-29", "nivel_educativo": "Secundaria",
            "region_natural": "Sierra", "area": "Rural", "edad": 24,
            "item_autolesion": 2, "phq9_score": 21}),
        ("Perfil inválido (edad incoherente)", {
            "sexo": "Mujer", "grupo_etario": "60+", "nivel_educativo": "Superior",
            "region_natural": "Costa", "area": "Urbano", "edad": 25}),
    ]

    for titulo, perfil in casos:
        print("\n" + "=" * 78)
        print(titulo)
        print("=" * 78)
        r = interpretar_perfil(perfil)
        print(r["texto"])
        print(f"\n[modo: {r['modo']}]")
        print("Trazas:", " → ".join(f"{t['nodo']} ({t['duracion_ms']:.0f} ms)"
                                    for t in r["trazas"]))

    d = exportar_diagrama()
    print(f"\nDiagrama del grafo: {d}")
