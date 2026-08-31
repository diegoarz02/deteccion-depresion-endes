"""Catálogo de recursos de ayuda y detección de crisis.

Dos piezas que existen por la misma razón: **el modelo de lenguaje no puede
generar un teléfono, una URL ni una respuesta ante una crisis.**

Un modelo alucina con naturalidad. Que invente una cifra en un párrafo es
molesto; que invente el número de una línea de ayuda para alguien que la
necesita es un daño real. Por eso los datos de contacto salen de un archivo
verificado y el modelo solo puede pedirlos por su identificador.

La detección de crisis, por lo mismo, es **determinista**: un control de
seguridad que depende de una llamada de red falla justo cuando más falta hace.
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path

log = logging.getLogger(__name__)

RUTA_CATALOGO = Path(__file__).resolve().parent / "recursos_ayuda.json"


@lru_cache(maxsize=1)
def catalogo() -> dict:
    """Carga el catálogo verificado de recursos."""
    return json.loads(RUTA_CATALOGO.read_text(encoding="utf-8"))


def obtener(identificador: str) -> dict | None:
    """Devuelve un recurso por su identificador, o ``None`` si no existe."""
    for r in catalogo()["recursos"]:
        if r["id"] == identificador:
            return r
    return None


def seleccionar(situaciones: list[str], maximo: int = 3) -> list[dict]:
    """Selecciona los recursos pertinentes para las situaciones indicadas.

    Parameters
    ----------
    situaciones : list of str
        Etiquetas como ``"crisis"``, ``"violencia_pareja"`` o
        ``"sintomas_depresivos"``.
    maximo : int, default 3
        Cuántos devolver como máximo. Una lista larga de teléfonos no ayuda a
        nadie: se ordenan por prioridad y se corta.

    Returns
    -------
    list of dict
        Recursos ordenados por prioridad.
    """
    etiquetas = set(situaciones) | {"siempre"}
    elegidos = [r for r in catalogo()["recursos"]
                if etiquetas & set(r.get("cuando_ofrecerlo", []))]
    elegidos.sort(key=lambda r: r["prioridad"])
    return elegidos[:maximo]


def formatear(recursos: list[dict]) -> str:
    """Convierte una lista de recursos en texto legible para el usuario."""
    lineas = []
    for r in recursos:
        cabecera = f"**{r['nombre']}**"
        if r.get("telefono"):
            cabecera += f" — marca **{r['telefono']}**"
        lineas.append(cabecera)
        lineas.append(f"  {r['descripcion']}")
        detalles = []
        if r.get("gratuito"):
            detalles.append("gratuito")
        if r.get("horario"):
            detalles.append(r["horario"].lower())
        if detalles:
            lineas.append(f"  ({', '.join(detalles)})")
        lineas.append("")
    return "\n".join(lineas).strip()


def identificadores_validos() -> set[str]:
    """Devuelve los identificadores que el modelo puede usar."""
    return {r["id"] for r in catalogo()["recursos"]}


def telefonos_validos() -> set[str]:
    """Teléfonos que pueden aparecer en una respuesta. Cualquier otro se bloquea."""
    t = {r["telefono"] for r in catalogo()["recursos"] if r.get("telefono")}
    for r in catalogo()["recursos"]:
        for c in r.get("canales_alternativos", []):
            if c["tipo"] == "WhatsApp":
                t.add(c["valor"])
    return t


def urls_validas() -> set[str]:
    """URLs que pueden aparecer en una respuesta."""
    return {r["url"] for r in catalogo()["recursos"] if r.get("url")}


# ─────────────────────────────────────────────────────────────────────
# Detección de crisis
# ─────────────────────────────────────────────────────────────────────

#: Umbral del ítem sensible del PHQ-9 a partir del cual se activa la crisis.
#: El ítem va de 0 a 3; cualquier respuesta distinta de "para nada" basta.
UMBRAL_ITEM_SENSIBLE = 1

#: Puntaje PHQ-9 en rango severo.
UMBRAL_PHQ9_SEVERO = 20

#: Señales en texto libre. Se buscan con generosidad: un falso positivo cuesta
#: mostrar un mensaje de ayuda de más; un falso negativo cuesta mucho más.
SENALES_TEXTO = [
    r"\bsuicid", r"\bmatarme\b", r"\bquitarme la vida\b", r"\bacabar con todo\b",
    # Las raíces se dejan abiertas por el final a propósito: «no quiero seguir
    # vivir» no lo dice nadie, lo que se escribe es «viviendo». Exigir la forma
    # exacta del infinitivo convertía la conjugación más natural en un falso
    # negativo, que es justo el error que este detector no se puede permitir.
    r"\bno quiero (seguir )?vivi(r|endo)\b", r"\bhacerme da[ñn]o\b", r"\bautolesi",
    r"\bmejor (si )?no estuviera\b", r"\bdesaparecer para siempre\b",
    r"\bno vale la pena (seguir|vivir|vivir m[aá]s)\b", r"\bquiero morir(me)?\b",
    r"\bpensamientos de muerte\b", r"\bcortarme\b",
    r"\bya no (quiero|puedo) (seguir|m[aá]s)\b", r"\bno le veo sentido a (la )?vida\b",
]

_SENALES = [re.compile(p, re.I) for p in SENALES_TEXTO]


def detectar_crisis(perfil: dict | None = None, prediccion: dict | None = None,
                    texto: str = "") -> dict:
    """Decide si la consulta debe tratarse como una situación de crisis.

    Se activa por cualquiera de tres vías, y basta una:

    1. El ítem sensible del PHQ-9 (pensamientos de hacerse daño) viene elevado.
    2. El puntaje total está en rango severo.
    3. El texto libre contiene señales de crisis.

    Returns
    -------
    dict
        ``hay_crisis``, ``motivos`` y ``origen``.
    """
    motivos = []
    perfil = perfil or {}

    item = perfil.get("item_autolesion")
    if item is not None:
        try:
            if float(item) >= UMBRAL_ITEM_SENSIBLE:
                motivos.append("respuesta elevada en el ítem sensible del PHQ-9")
        except (TypeError, ValueError):
            pass

    puntaje = perfil.get("phq9_score")
    if puntaje is not None:
        try:
            if float(puntaje) >= UMBRAL_PHQ9_SEVERO:
                motivos.append(f"puntaje PHQ-9 en rango severo ({puntaje})")
        except (TypeError, ValueError):
            pass

    if texto:
        for p in _SENALES:
            if p.search(texto):
                motivos.append("señal de crisis en el texto de la consulta")
                break

    return {"hay_crisis": bool(motivos), "motivos": motivos,
            "origen": "detección determinista, previa a cualquier llamada al modelo"}


def respuesta_crisis() -> tuple[str, list[dict]]:
    """Devuelve el texto fijo de crisis y sus recursos.

    No lo redacta un modelo. Está escrito de antemano, revisado, y evita
    cualquier detalle sobre métodos.
    """
    plantilla = catalogo()["plantilla_crisis"]
    recursos = [obtener(i) for i in plantilla["recursos"]]
    return plantilla["texto"], [r for r in recursos if r]
