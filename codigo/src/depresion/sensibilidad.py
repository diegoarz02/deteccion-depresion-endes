"""Análisis de sensibilidad sobre el nivel educativo faltante.

Contexto
--------
En el dataset final, ``educacion_grupo`` es nula para 1 145 de las 30 226
personas del análisis (3,8 %). No son datos perdidos al azar: en el cuestionario
de salud, ``QS24`` («¿asistió a la escuela?») filtra a ``QS25N`` («nivel que
aprobó»), y las personas que respondieron «No» (``QS24 == 2``) no tienen nivel
aprobado porque nunca asistieron. Es un salto estructural, no una omisión. El
grupo es en su gran mayoría de mujeres de 60 años o más, rurales y de zonas
altoandinas, con una prevalencia de tamizaje positivo mucho mayor que la media.

El modelo principal (casos completos) las excluye. Sus coeficientes son los que
sirve la API, y este módulo ofrece lo necesario para cuantificar el efecto de
esa exclusión sin modificarlo.
"""

from __future__ import annotations

import logging

import pandas as pd

from . import config as cfg

log = logging.getLogger(__name__)

SIN_EDUCACION = "Sin educación"


def educacion_cuatro_niveles(df: pd.DataFrame) -> pd.DataFrame:
    """Añade ``educacion_4``: ``educacion_grupo`` más la categoría «Sin educación».

    Las nulas de ``educacion_grupo`` se leen como «Sin educación». La lectura se
    comprueba contra ``QS24`` del archivo original con
    :func:`verificar_sin_educacion`; mientras no se compruebe, es una hipótesis
    respaldada por el patrón de salto del cuestionario.
    """
    out = df.copy()
    niveles = [SIN_EDUCACION, "Primaria o menos", "Secundaria", "Superior"]
    texto = out.educacion_grupo.astype(object).where(out.educacion_grupo.notna(), SIN_EDUCACION)
    out["educacion_4"] = pd.Categorical(texto, categories=niveles, ordered=True)
    return out


def verificar_sin_educacion(df: pd.DataFrame) -> dict:
    """Comprueba contra ``QS24`` del .sav que «sin nivel» equivale a «nunca asistió».

    Devuelve un diccionario con el resultado. Si el archivo original no está
    disponible (por ejemplo, en una máquina sin los microdatos) devuelve
    ``{"verificado": False}`` en lugar de fallar: el dataset se versiona, los
    .sav no.
    """
    ruta = cfg.FUENTE_SAV / cfg.ARCHIVO_CSALUD
    if not ruta.exists():
        return {"verificado": False, "motivo": f"no existe {ruta}"}
    try:
        import pyreadstat
        crudo, _ = pyreadstat.read_sav(str(ruta), apply_value_formats=False,
                                       usecols=["HHID", "QSNUMERO", "QS24", "QS25N"])
    except Exception as e:  # noqa: BLE001 - la verificación no debe romper el análisis
        return {"verificado": False, "motivo": str(e)}

    nunca = crudo[crudo.QS24 == 2]
    coinciden = bool(nunca.QS25N.isna().all())
    clave = ["HHID", "QSNUMERO"]
    union = df.merge(crudo[[*clave, "QS24"]], on=clave, how="left")
    nulas = union[union.educacion_grupo.isna()]
    return {
        "verificado": True,
        "nunca_asistio_total": int(len(nunca)),
        "nunca_asistio_con_nivel_nulo": int(nunca.QS25N.isna().sum()),
        "salto_estructural": coinciden,
        "nulas_en_analisis": int(len(nulas)),
        "nulas_que_nunca_asistieron": int((nulas.QS24 == 2).sum()),
    }
