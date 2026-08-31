"""Unión de las bases y limpieza de códigos, según la auditoría de §7.

Principio rector: **nunca recodificar por convención**. Cada variable se
limpia consultando sus etiquetas reales (``meta.variable_value_labels``),
no asumiendo que 8 = "No sabe" y 9 = "Rehúsa".
"""

from __future__ import annotations

import logging
import re

import numpy as np
import pandas as pd

from . import config as cfg
from .io import Metadatos

log = logging.getLogger(__name__)

# Patrones que identifican una etiqueta de "dato faltante" de verdad
_PATRON_NO_SABE = re.compile(r"no\s*sabe|no\s*recuerda|no\s*est[aá]\s*segur", re.I)
_PATRON_REHUSA = re.compile(r"reh[uú]sa|se\s*niega|no\s*responde", re.I)


class ErrorDeUnion(RuntimeError):
    """Se lanza si el match por HHID cae por debajo del umbral aceptable."""


# ─────────────────────────────────────────────────────────────────────
# 1. Unión
# ─────────────────────────────────────────────────────────────────────


def unir_bases(
    csalud: pd.DataFrame,
    rech0: pd.DataFrame,
    columnas_rech0: list[str] | None = None,
) -> pd.DataFrame:
    """Une CSALUD01 con RECH0 por HHID y valida el match.

    El estrato (``HV022``) y las variables geográficas solo existen en RECH0,
    de modo que esta unión es requisito para poder declarar el diseño muestral.

    Parameters
    ----------
    csalud : pandas.DataFrame
        Cuestionario de salud, personas de 15 años a más.
    rech0 : pandas.DataFrame
        Registro del hogar.
    columnas_rech0 : list of str, optional
        Columnas de RECH0 a traer. Por defecto, las de diseño y geografía.

    Returns
    -------
    pandas.DataFrame
        CSALUD01 con las columnas de RECH0 añadidas.

    Raises
    ------
    ErrorDeUnion
        Si el porcentaje de match es inferior a ``config.MATCH_MINIMO``.
    """
    if columnas_rech0 is None:
        columnas_rech0 = [
            cfg.VAR_ESTRATO, cfg.VAR_DEPARTAMENTO, cfg.VAR_DOMINIO,
            cfg.VAR_AREA, cfg.VAR_ALTITUD, cfg.VAR_UBIGEO,
            "HV026", "HV009", "HV001",
            # Georreferenciación: se incorporan en la segunda corrida.
            "LONGITUDX", "LATITUDY", "NOMCCPP",
        ]
    columnas_rech0 = [c for c in columnas_rech0 if c in rech0.columns]

    izq = csalud[cfg.LLAVE].astype(str).str.strip()
    der = rech0[cfg.LLAVE].astype(str).str.strip()

    if der.duplicated().any():
        n = int(der.duplicated().sum())
        raise ErrorDeUnion(f"RECH0 tiene {n} HHID duplicados: la unión sería ambigua.")

    match = izq.isin(set(der)).mean()
    log.info("Match por %s: %.2f%% (%s de %s)",
             cfg.LLAVE, match * 100, f"{izq.isin(set(der)).sum():,}", f"{len(izq):,}")
    if match < cfg.MATCH_MINIMO:
        raise ErrorDeUnion(
            f"Match del {match:.2%}, por debajo del mínimo "
            f"({cfg.MATCH_MINIMO:.0%}). Pipeline detenido."
        )

    geo = rech0.assign(_k=der).set_index("_k")[columnas_rech0]
    out = csalud.assign(_k=izq).join(geo, on="_k").drop(columns="_k")

    faltan = out[columnas_rech0].isna().all(axis=1).sum()
    if faltan:
        log.warning("%s filas quedaron sin datos de RECH0", f"{faltan:,}")
    return out


# ─────────────────────────────────────────────────────────────────────
# 2. Inventario e inspección de códigos
# ─────────────────────────────────────────────────────────────────────


def inventariar_codigos_especiales(
    df: pd.DataFrame, meta: Metadatos, codigos: tuple[int, ...] = (8, 9)
) -> pd.DataFrame:
    """Construye el inventario de variables que contienen códigos especiales.

    Para cada variable donde aparecen los ``codigos``, reporta cuántas veces
    aparecen, su etiqueta real y si esa etiqueta corresponde a dato faltante.
    Es la evidencia que sustenta la decisión de limpieza de cada variable.

    Parameters
    ----------
    df : pandas.DataFrame
        Datos crudos.
    meta : Metadatos
        Metadatos del archivo SPSS.
    codigos : tuple of int, default (8, 9)
        Códigos a rastrear.

    Returns
    -------
    pandas.DataFrame
        Una fila por variable, con conteos, etiquetas y decisión propuesta.
    """
    filas = []
    for c in df.columns:
        s = df[c]
        if s.dtype.kind not in "fi":
            continue
        s = s.dropna()
        if s.empty or s.max() > 100:  # descarta continuas (peso, talla, presión)
            continue
        presentes = {k: int((s == k).sum()) for k in codigos}
        if not any(presentes.values()):
            continue
        vl = meta.valores(c)
        etiquetas = {k: vl.get(float(k), "—SIN ETIQUETA—") for k in codigos}
        es_faltante = {
            k: bool(_PATRON_NO_SABE.search(str(etiquetas[k])) or
                    _PATRON_REHUSA.search(str(etiquetas[k])))
            for k in codigos
        }
        filas.append({
            "variable": c,
            "descripcion": meta.etiqueta(c)[:70],
            "n_validos": int(s.notna().sum()),
            "maximo": float(s.max()),
            **{f"n_{k}": presentes[k] for k in codigos},
            **{f"etiqueta_{k}": etiquetas[k] for k in codigos},
            **{f"es_faltante_{k}": es_faltante[k] for k in codigos},
            "decision": (
                "recodificar a NaN"
                if any(es_faltante.values())
                else "REVISAR — el código no es dato faltante"
            ),
        })
    out = pd.DataFrame(filas)
    log.info("Inventario de códigos %s: %s variables afectadas", codigos, len(out))
    return out


def limpiar_codigos_faltantes(
    df: pd.DataFrame, meta: Metadatos, codigos: tuple[int, ...] = (8, 9)
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convierte a NaN los códigos especiales, pero SOLO donde son faltantes.

    Una variable se limpia únicamente si su etiqueta declara explícitamente
    "No sabe", "No recuerda" o "Rehúsa". Si el código carece de etiqueta o
    significa otra cosa (mes, lengua materna, categoría ordinal), se deja
    intacto y se reporta.

    Parameters
    ----------
    df : pandas.DataFrame
        Datos a limpiar.
    meta : Metadatos
        Metadatos con las etiquetas reales.
    codigos : tuple of int, default (8, 9)
        Códigos candidatos a faltante.

    Returns
    -------
    tuple of (pandas.DataFrame, pandas.DataFrame)
        El DataFrame limpio y la bitácora de lo que se hizo por variable.
    """
    inv = inventariar_codigos_especiales(df, meta, codigos)
    out = df.copy()
    bitacora = []

    for _, r in inv.iterrows():
        var = r["variable"]
        for k in codigos:
            if not r[f"es_faltante_{k}"] or r[f"n_{k}"] == 0:
                continue
            out.loc[out[var] == k, var] = np.nan
            bitacora.append({
                "variable": var,
                "codigo": k,
                "etiqueta": r[f"etiqueta_{k}"],
                "casos_convertidos": r[f"n_{k}"],
                "accion": "-> NaN",
            })

    intactas = inv[inv["decision"].str.startswith("REVISAR")]
    for _, r in intactas.iterrows():
        bitacora.append({
            "variable": r["variable"],
            "codigo": "8/9",
            "etiqueta": f"{r['etiqueta_8']} / {r['etiqueta_9']}",
            "casos_convertidos": 0,
            "accion": "INTACTA — el código no es dato faltante",
        })

    bit = pd.DataFrame(bitacora)
    log.info("Códigos limpiados en %s variables; %s dejadas intactas",
             bit[bit.accion == "-> NaN"].variable.nunique() if len(bit) else 0,
             len(intactas))
    return out, bit


# ─────────────────────────────────────────────────────────────────────
# 3. Correcciones específicas verificadas en la auditoría
# ─────────────────────────────────────────────────────────────────────


def corregir_qs711(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Documenta y valida la codificación real de QS711.

    El diccionario del INEI etiqueta los códigos 1, 2, 8 y 9, pero en los
    datos aparecen 1, 2, 3 y 4 — la misma escala que su pregunta gemela
    QS710. No hay que transformar nada: hay que **no** destruir los códigos
    3 y 4, que son los casos de violencia más severa.

    Returns
    -------
    tuple of (pandas.DataFrame, dict)
        El DataFrame sin cambios en los valores, y un informe de verificación.
    """
    v = cfg.VAR_VIOLENCIA_OBJETO
    s = df[v]
    informe = {
        "variable": v,
        "codigos_en_datos": sorted(s.dropna().unique().tolist()),
        "codigos_8_9_presentes": bool(s.isin([8, 9]).any()),
        "casos_severos_3_4": int(s.isin([3, 4]).sum()),
        "escala_aplicada": cfg.ESCALA_VIOLENCIA,
        "nota": (
            "El diccionario SPSS del INEI etiqueta 8 y 9 donde los datos "
            "graban 3 y 4. Se conserva la escala ordinal 1-4 de QS710."
        ),
    }
    if informe["codigos_8_9_presentes"]:
        log.warning("QS711 SÍ contiene códigos 8/9: revisar el supuesto.")
    log.info("QS711 verificada: %s casos en categorías severas (3, 4)",
             informe["casos_severos_3_4"])
    return df, informe


def limpiar_antropometria(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convierte a NaN los códigos de no-medición de peso, talla y perímetro.

    Aplica el umbral ``>= 900`` **solo** a QS900, QS901 y QS907. La presión
    arterial no usa ese código: sus rangos son plausibles (sistólica 61-220,
    diastólica 40-142) y su faltante ya viene como NaN.

    Returns
    -------
    tuple of (pandas.DataFrame, pandas.DataFrame)
        DataFrame limpio y resumen de cuántos casos se marcaron por variable.
    """
    out = df.copy()
    filas = []
    for v in (cfg.VAR_PESO_KG, cfg.VAR_TALLA_CM, cfg.VAR_PERIMETRO_ABD):
        antes = int(out[v].notna().sum())
        n_cod = int((out[v] >= cfg.UMBRAL_NO_MEDICION).sum())
        out.loc[out[v] >= cfg.UMBRAL_NO_MEDICION, v] = np.nan
        filas.append({
            "variable": v,
            "n_antes": antes,
            "codigos_no_medicion": n_cod,
            "n_despues": int(out[v].notna().sum()),
            "minimo": float(out[v].min()),
            "maximo": float(out[v].max()),
        })

    for v in cfg.PRESION_SISTOLICA + cfg.PRESION_DIASTOLICA:
        filas.append({
            "variable": v,
            "n_antes": int(out[v].notna().sum()),
            "codigos_no_medicion": 0,
            "n_despues": int(out[v].notna().sum()),
            "minimo": float(out[v].min()),
            "maximo": float(out[v].max()),
        })

    res = pd.DataFrame(filas)
    log.info("Antropometría limpiada:\n%s", res.to_string(index=False))
    return out, res


def verificar_saltos(df: pd.DataFrame) -> pd.DataFrame:
    """Verifica que cada cadena de saltos sea estructuralmente coherente.

    Una *violación* es un caso con dato presente sin cumplir el filtro que
    debería habilitarlo. Un salto limpio tiene cero violaciones, y entonces
    su NaN significa "no aplica", no "dato perdido".

    Returns
    -------
    pandas.DataFrame
        Una fila por variable hija, con presentes, violaciones y veredicto.
    """
    items = cfg.ITEMS_PHQ9
    phq_ok = df[items].notna().all(axis=1)

    cadenas = [
        ("Violencia", "QS709 == 1", df[cfg.VAR_TUVO_PAREJA].eq(1),
         [cfg.VAR_VIOLENCIA_GOLPE, cfg.VAR_VIOLENCIA_OBJETO]),
        ("Salud mental 12m", "QS703 == 1", df["QS703"].eq(1),
         [f"QS704{x}" for x in "ABCDEFGHI"]),
        ("Funcionalidad", "algún QS700x > 0", df[items].gt(0).any(axis=1) & phq_ok,
         ["QS702"]),
        ("Alcohol N1", "QS209 == 1", df[cfg.VAR_ALCOHOL_FRECUENTE].eq(1),
         ["QS713", "QS714", "QS716", "QS717"]),
        # Subfiltro directo: QS715 solo se pregunta si QS714 fue "Sí".
        ("Alcohol N1 (subfiltro)", "QS714 == 1", df["QS714"].eq(1), ["QS715"]),
        ("Alcohol N2", "algún QS713-717 == 1",
         df[cfg.ITEMS_DEPENDENCIA_N1].eq(1).any(axis=1),
         ["QS719", "QS720", "QS721", "QS723", "QS726", "QS727", "QS728", "QS729"]),
        # Subfiltros "si respondió Sí, salta la siguiente": el criterio ya quedó
        # satisfecho y la pregunta siguiente sería redundante.
        ("Alcohol N2 (subfiltro)", "llegó a N2 y QS721 != 1",
         df[cfg.ITEMS_DEPENDENCIA_N1].eq(1).any(axis=1) & df["QS721"].ne(1), ["QS722"]),
        ("Alcohol N2 (subfiltro)", "llegó a N2 y QS723 != 1",
         df[cfg.ITEMS_DEPENDENCIA_N1].eq(1).any(axis=1) & df["QS723"].ne(1), ["QS724"]),
        ("Alcohol N2 (subfiltro)", "QS724 respondida y != 1",
         df["QS724"].notna() & df["QS724"].ne(1), ["QS725"]),
        ("Tabaco 30d", "QS200 == 1", df[cfg.VAR_TABACO_12M].eq(1),
         [cfg.VAR_TABACO_30D]),
        ("Tabaco diario", "QS201 == 1", df[cfg.VAR_TABACO_30D].eq(1),
         [cfg.VAR_TABACO_DIARIO]),
    ]

    filas = []
    for nombre, regla, filtro, hijas in cadenas:
        for h in hijas:
            if h not in df.columns:
                continue
            pres = df[h].notna()
            filas.append({
                "cadena": nombre,
                "filtro": regla,
                "variable": h,
                "esperados": int(filtro.sum()),
                "presentes": int(pres.sum()),
                "violaciones": int((pres & ~filtro).sum()),
                "faltantes_en_filtro": int((~pres & filtro).sum()),
            })
    res = pd.DataFrame(filas)
    res["veredicto"] = np.where(
        res.violaciones == 0, "SALTO LIMPIO — NaN = no aplica", "REVISAR"
    )
    n_mal = int((res.violaciones > 0).sum())
    if n_mal:
        log.warning("%s variables con violaciones de salto", n_mal)
    else:
        log.info("Los %s saltos verificados son limpios (0 violaciones)", len(res))
    return res
