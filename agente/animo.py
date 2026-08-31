"""Selección de frases de ánimo desde un banco cerrado.

Mismo patrón que el catálogo de recursos, y por la misma razón: **el modelo
elige un identificador, el código sustituye el texto**. Una cita inventada o mal
atribuida en un trabajo académico es un error que arrastra todo lo demás, y es
justo el tipo de fallo que un modelo comete sin dar ninguna señal.

El banco vive en ``contenido/frases_animo.json`` y solo contiene frases de obras
de ficción. No se atribuye ninguna a una persona real.

Regla que no se negocia
-----------------------
**Si el nodo de crisis está activo, no se muestra ninguna frase.** Ahí va la
plantilla fija con la Línea 113 y nada más. Una frase de ánimo en mitad de una
crisis se lee como minimizar lo que la persona está diciendo.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

RUTA = Path(__file__).resolve().parents[1] / "contenido" / "frases_animo.json"

#: Qué tono pide cada categoría de resultado. La lógica es deliberada: a mayor
#: prevalencia del grupo, **menos** aliento y más compañía. Empujar a alguien
#: que ya se siente señalado suena a exigencia; acompañarlo, no.
TONO_POR_CATEGORIA = {"bajo": "sereno", "medio": "aliento", "alto": "compania"}


def banco() -> dict:
    """Carga el banco de frases una sola vez."""
    if not hasattr(banco, "_cache"):
        banco._cache = (json.loads(RUTA.read_text(encoding="utf-8"))
                        if RUTA.exists() else {"frases": []})
        if not RUTA.exists():
            log.warning("No existe %s: no se mostrarán frases de ánimo", RUTA.name)
    return banco._cache


def identificadores() -> set[str]:
    """Identificadores válidos, para que el guardarraíl pueda comprobarlos."""
    return {f["id"] for f in banco()["frases"]}


def por_id(identificador: str) -> dict | None:
    """Devuelve una frase por su identificador, o None si no existe."""
    return next((f for f in banco()["frases"] if f["id"] == identificador), None)


def por_tono(tono: str) -> list[dict]:
    """Devuelve las frases de un tono dado."""
    return [f for f in banco()["frases"] if f["tono"] == tono]


def elegir(categoria: str = "bajo", hay_crisis: bool = False,
           semilla: int | None = None) -> dict | None:
    """Elige una frase para el resultado dado.

    Parameters
    ----------
    categoria : str
        ``bajo``, ``medio`` o ``alto``. Determina el tono.
    hay_crisis : bool
        Si el nodo de crisis se activó. En ese caso **no se devuelve nada**.
    semilla : int, optional
        Índice para elegir de forma determinista. Sin él se toma la primera del
        tono, que es la mejor de su grupo: el orden del JSON no es casual.

    Returns
    -------
    dict or None
        La frase completa, o ``None`` si hay crisis o el banco está vacío.
    """
    if hay_crisis:
        return None
    candidatas = por_tono(TONO_POR_CATEGORIA.get(categoria, "sereno"))
    if not candidatas:
        candidatas = banco()["frases"]
    if not candidatas:
        return None
    return candidatas[semilla % len(candidatas)] if semilla is not None else candidatas[0]


def formatear(frase: dict | None) -> str:
    """Compone el bloque de texto de una frase, con su fuente.

    Las adaptadas se marcan como tales. Presentar una paráfrasis como cita
    literal es exactamente el error que este módulo existe para evitar.
    """
    if not frase:
        return ""
    fuente = frase["fuente"]
    if not frase.get("verificada", False) and not fuente.startswith("Inspirado"):
        fuente = f"Adaptado de {fuente}"
    return f"«{frase['texto']}»\n— {fuente}"
