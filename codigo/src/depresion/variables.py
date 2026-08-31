"""Construcción de las variables analíticas del proyecto.

Regla central para las cadenas de saltos: el ``NaN`` que produce un filtro
del cuestionario significa **"no aplica"**, no "dato perdido". Cada función
codifica ese "no aplica" de forma explícita y deja constancia de la regla
exacta usada, que después alimenta el diccionario de variables.

Sin esta disciplina, un *complete-case* ingenuo reduciría la muestra de
~30 000 a ~900 casos.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from . import config as cfg

log = logging.getLogger(__name__)

# Bitácora de reglas: variable construida -> regla de recodificación exacta.
REGLAS: dict[str, str] = {}

#: Variables que se documentan al importar el módulo, no dentro de la función
#: que las construye. Son de dos clases: las que llegan tal cual de la ENDES
#: —donde la «regla» es decir de qué pregunta vienen— y las derivadas de una
#: línea, cuya regla cabe entera aquí. Sin este bloque salían al diccionario
#: con la columna en blanco, que es peor que no tener diccionario: aparenta
#: estar documentado.
_DIRECTAS: dict[str, str] = {
    "HHID": "Identificador del hogar en la ENDES. Con QSNUMERO forma la llave.",
    "QSNUMERO": "Número de orden de la persona dentro del hogar.",
    "peso_kg": "QS900 en kilogramos, tras convertir a NaN los códigos de "
               "no-medición (>= 900).",
    "talla_cm": "QS901 en centímetros, con la misma limpieza de códigos.",
    "perimetro_abdominal": "QS903 en centímetros, con la misma limpieza.",
    "presion_sistolica": "Promedio de las dos tomas de presión sistólica.",
    "presion_diastolica": "Promedio de las dos tomas de presión diastólica.",
    "phq9_completo": "1 si los nueve ítems del PHQ-9 están presentes; 0 si falta "
                     "alguno. Es la marca que separa el faltante estructural del "
                     "aleatorio.",
    "sexo": "QS24 recodificada a etiquetas: 1 = Hombre, 2 = Mujer.",
    "es_mujer": "1 si sexo = Mujer; 0 si Hombre. NaN si el sexo falta.",
    "educacion": "QS25 en sus cuatro niveles originales, como categoría ordenada.",
    "edad_topeada": "1 si la edad declarada es 97, el tope de la encuesta "
                    "('97 o más años'). Marca que ese valor está censurado.",
    "es_rural": "1 si el área de residencia es rural; 0 si urbana.",
    "departamento_norm": "Nombre del departamento sin tildes ni espacios "
                         "sobrantes, para poder cruzarlo con los shapefiles.",
    "alcohol_alguna_vez": "QS400 = Sí (consumió alcohol alguna vez en la vida).",
    "consumo_30d": "QS402 = Sí (consumo en los últimos 30 días). Se fija en 0 "
                   "para quienes no bebieron en 12 meses: es un salto de "
                   "cuestionario, no un dato ausente.",
    "alcohol_categoria": "Resumen ordinal del patrón de consumo: sin consumo, "
                         "consumo sin criterios, abuso, dependencia.",
    "tabaco_categoria": "Resumen ordinal del consumo de tabaco: nunca, "
                        "exfumador, ocasional, diario.",
    "tuvo_pareja": "QS800 = Sí (tuvo alguna vez pareja). Define la subpoblación "
                   "a la que se le pregunta por violencia.",
    "violencia_objeto": "1 si la pareja lanzó un objeto más de una vez. Solo "
                        "definida en quienes tuvieron pareja; NaN en el resto.",
    "violencia_max": "Máximo entre violencia por golpe y por objeto: el peor de "
                     "los dos indicadores, no su suma.",
    "imc_categoria": "Categoría de la OMS: bajo peso (< 18,5), normal "
                     "(18,5-24,9), sobrepeso (25-29,9), obesidad (>= 30).",
    "tiene_cronica": "1 si n_cronicas >= 1 (al menos hipertensión, diabetes u "
                     "obesidad).",
    "tiene_peso": "1 si la persona tiene ponderador Peso15_AMAS asignado. Sin "
                  "él no puede entrar al análisis con diseño complejo.",
    "en_analisis": "1 si la persona tiene PHQ-9 completo y ponderador. Es la "
                   "población de análisis del flujograma STROBE (n = 30 226).",
}


def _regla(nombre: str, texto: str) -> None:
    """Registra la regla de construcción de una variable."""
    REGLAS[nombre] = " ".join(texto.split())


for _nombre, _texto in _DIRECTAS.items():
    _regla(_nombre, _texto)

# Los nueve ítems del PHQ-9 se documentan desde cfg.ETIQUETAS_PHQ9, no a mano.
# La ENDES NO usa el orden canónico del instrumento: su ítem I es «se sintió mal
# consigo mismo», que en el PHQ-9 original es el 6, y el ítem sensible —
# pensamientos de hacerse daño — es el H, no el I. Escribir el orden estándar de
# memoria produce una tabla que parece correcta y señala el ítem equivocado como
# sensible, que es justo el error que no puede pasar aquí.
for _item in cfg.ITEMS_PHQ9:
    _nota = (" No se analiza ni se publica como desenlace independiente (ética, "
             "§15.3); alimenta la detección de crisis del agente."
             if _item == cfg.ITEM_SENSIBLE else "")
    _regla(_item, f"Ítem del PHQ-9: «{cfg.ETIQUETAS_PHQ9[_item]}». Escala 0-3, "
                  f"tal cual de la encuesta.{_nota}")


def _si_no(s: pd.Series) -> pd.Series:
    """Convierte una variable ENDES 1=Sí / 2=No en booleana (1/0), resto NaN."""
    return s.map({1: 1, 2: 0}).astype("Float64")


def _cond(s) -> np.ndarray:
    """Convierte una condición posiblemente nulable en un array bool de numpy.

    ``np.select`` no acepta el ``boolean`` nulable de pandas: los NaN deben
    resolverse antes, y aquí se resuelven como *falso* (no cumple la condición).
    """
    return np.asarray(pd.Series(s).fillna(False).astype(bool))


# ─────────────────────────────────────────────────────────────────────
# 1. DESENLACE
# ─────────────────────────────────────────────────────────────────────


def construir_phq9(df: pd.DataFrame) -> pd.DataFrame:
    """Construye el puntaje PHQ-9 y sus derivados.

    El puntaje solo se calcula para quienes tienen los **nueve** ítems
    respondidos; con un ítem faltante el puntaje no es comparable y se deja
    en NaN (no se imputa).

    Parameters
    ----------
    df : pandas.DataFrame
        Datos con los ítems ``QS700A``…``QS700I``.

    Returns
    -------
    pandas.DataFrame
        Copia con ``phq9_score``, ``depresion_bin``, ``depresion_leve_bin``,
        ``phq9_categoria`` y ``phq9_completo``.
    """
    out = df.copy()
    items = cfg.ITEMS_PHQ9
    completo = out[items].notna().all(axis=1)

    out["phq9_completo"] = completo.astype(int)
    out["phq9_score"] = out[items].sum(axis=1).where(completo)
    out["depresion_bin"] = (out.phq9_score >= cfg.CORTE_DEPRESION).astype("Float64").where(completo)
    out["depresion_leve_bin"] = (out.phq9_score >= cfg.CORTE_DEPRESION_LEVE).astype("Float64").where(completo)

    cats = pd.Series(pd.NA, index=out.index, dtype="object")
    for lo, hi, etq in cfg.CATEGORIAS_PHQ9:
        cats[out.phq9_score.between(lo, hi)] = etq
    out["phq9_categoria"] = pd.Categorical(
        cats, categories=[e for _, _, e in cfg.CATEGORIAS_PHQ9], ordered=True
    )

    _regla("phq9_score",
           "Suma de QS700A..QS700I (escala 0-3 cada uno). Solo si los 9 ítems "
           "están presentes; con cualquier ítem faltante -> NaN, sin imputar.")
    _regla("depresion_bin", f"1 si phq9_score >= {cfg.CORTE_DEPRESION}; 0 si no. NaN si PHQ incompleto.")
    _regla("depresion_leve_bin", f"1 si phq9_score >= {cfg.CORTE_DEPRESION_LEVE}; 0 si no.")
    _regla("phq9_categoria", "Mínima 0-4 / Leve 5-9 / Moderada 10-14 / Mod-severa 15-19 / Severa 20-27.")

    log.info("PHQ-9: N completo=%s, media=%.3f, prevalencia >=%d: %.2f%%",
             f"{int(completo.sum()):,}", out.phq9_score.mean(),
             cfg.CORTE_DEPRESION, out.depresion_bin.mean() * 100)
    return out


# ─────────────────────────────────────────────────────────────────────
# 2. SOCIODEMOGRÁFICAS
# ─────────────────────────────────────────────────────────────────────


def construir_sociodemograficas(df: pd.DataFrame) -> pd.DataFrame:
    """Construye edad, grupo etario, sexo, educación y área."""
    out = df.copy()

    out["edad"] = out[cfg.VAR_EDAD]
    out["edad_topeada"] = (out.edad == cfg.EDAD_TOPE).astype(int)
    grupos = pd.Series(pd.NA, index=out.index, dtype="object")
    for lo, hi, etq in cfg.GRUPOS_ETARIOS:
        grupos[out.edad.between(lo, hi)] = etq
    out["grupo_etario"] = pd.Categorical(
        grupos, categories=[e for _, _, e in cfg.GRUPOS_ETARIOS], ordered=True
    )

    out["sexo"] = out[cfg.VAR_SEXO].map({1: "Hombre", 2: "Mujer"})
    out["es_mujer"] = (out[cfg.VAR_SEXO] == 2).astype("Float64").where(out[cfg.VAR_SEXO].notna())

    niveles = ["Inicial", "Primaria", "Secundaria",
               "Superior no univ.", "Superior univ.", "Postgrado"]
    out["educacion"] = pd.Categorical(
        out[cfg.VAR_EDUCACION].map(dict(enumerate(niveles))),
        categories=niveles, ordered=True,
    )
    # Agrupación operativa: Inicial y Primaria tienen n pequeño en Inicial (66)
    out["educacion_grupo"] = pd.Categorical(
        out[cfg.VAR_EDUCACION].map(
            {0: "Primaria o menos", 1: "Primaria o menos", 2: "Secundaria",
             3: "Superior", 4: "Superior", 5: "Superior"}
        ),
        categories=["Primaria o menos", "Secundaria", "Superior"], ordered=True,
    )

    out["area"] = out[cfg.VAR_AREA].map({1: "Urbano", 2: "Rural"})
    out["es_rural"] = (out[cfg.VAR_AREA] == 2).astype("Float64").where(out[cfg.VAR_AREA].notna())

    _regla("edad", f"QS23 tal cual (15-{cfg.EDAD_TOPE}). El valor {cfg.EDAD_TOPE} es un tope: '{cfg.EDAD_TOPE} o más años'.")
    _regla("grupo_etario", "15-19 / 20-29 / 30-39 / 40-49 / 50-59 / 60+.")
    _regla("educacion_grupo", "QS25N agrupado: {0,1}=Primaria o menos, {2}=Secundaria, {3,4,5}=Superior.")
    _regla("area", "HV025: 1=Urbano, 2=Rural.")
    return out


def construir_geografia(df: pd.DataFrame, etiquetas_departamento: dict) -> pd.DataFrame:
    """Construye departamento, región natural y dominio INEI.

    La región natural **no existe** en ENDES y se deriva a nivel de
    conglomerado con la altitud (``HV040``), porque la altitud es fuertemente
    bimodal dentro de varios departamentos: clasificar Áncash entero como
    "Costa" o como "Sierra" sería incorrecto en cualquiera de los dos sentidos.

    Parameters
    ----------
    df : pandas.DataFrame
        Datos ya unidos con RECH0.
    etiquetas_departamento : dict
        Mapa código -> nombre de departamento (de ``HV024``).

    Returns
    -------
    pandas.DataFrame
        Copia con ``departamento``, ``departamento_norm``, ``altitud``,
        ``region_natural`` y ``dominio_inei``.
    """
    out = df.copy()

    out["departamento"] = out[cfg.VAR_DEPARTAMENTO].map(
        {k: str(v).strip() for k, v in etiquetas_departamento.items()}
    )
    out["departamento_norm"] = out.departamento.map(cfg.normalizar_texto)
    out["altitud"] = out[cfg.VAR_ALTITUD]

    en_occidente = out.departamento.isin(cfg.DEPARTAMENTOS_VERTIENTE_OCCIDENTAL)
    out["region_natural"] = pd.Categorical(
        np.where(
            out.altitud.isna(), None,
            np.where(out.altitud >= cfg.ALTITUD_SIERRA, "Sierra",
                     np.where(en_occidente, "Costa", "Selva")),
        ),
        categories=cfg.REGIONES_NATURALES,
    )

    ubigeo = out[cfg.VAR_UBIGEO].astype(str).str.zfill(6)
    es_lima_met = ubigeo.str[:4].isin(cfg.UBIGEO_LIMA_METROPOLITANA)
    out["dominio_inei"] = pd.Categorical(
        np.where(es_lima_met, "Lima Metropolitana", out.region_natural.astype(object)),
        categories=["Lima Metropolitana", "Costa", "Sierra", "Selva"],
    )

    _regla("region_natural",
           f"Derivada a nivel de conglomerado: Sierra si HV040 >= {cfg.ALTITUD_SIERRA} m; "
           "si no, Costa cuando el departamento pertenece a la vertiente occidental "
           "(Tumbes, Piura, Lambayeque, La Libertad, Áncash, Lima, Callao, Ica, "
           "Arequipa, Moquegua, Tacna); Selva en cualquier otro caso.")
    _regla("dominio_inei",
           "Lima Metropolitana si UBIGEO de provincia es 1501 (Lima) o 0701 (Callao); "
           "en caso contrario, la región natural.")
    _regla("departamento", "HV024 (etiquetas limpias; HV023 es idéntica pero trae espacios a la izquierda).")

    log.info("Región natural: %s", out.region_natural.value_counts().to_dict())
    return out


# ─────────────────────────────────────────────────────────────────────
# 3. CONDUCTUALES — ALCOHOL Y TABACO
# ─────────────────────────────────────────────────────────────────────


def construir_alcohol(df: pd.DataFrame) -> pd.DataFrame:
    """Construye el bloque de consumo de alcohol respetando la cadena de saltos.

    Cadena verificada en el cuestionario::

        QS206 (alguna vez)
          └─> QS208 (últimos 12 meses)
                └─> QS209 (12 o más días)
                      └─> QS713-717  (dependencia, nivel 1)
                            └─> QS719-729  (severidad, nivel 2)

    Quien nunca bebió no llega al bloque de dependencia: su "no aplica" se
    codifica como ``0`` síntomas, que es la lectura sustantiva correcta.
    """
    out = df.copy()

    out["alcohol_alguna_vez"] = _si_no(out[cfg.VAR_ALCOHOL_ALGUNA_VEZ])
    out["consumo_alcohol_12m"] = _si_no(out[cfg.VAR_ALCOHOL_12M])
    out.loc[out.alcohol_alguna_vez == 0, "consumo_alcohol_12m"] = 0

    out["consumo_frecuente"] = _si_no(out[cfg.VAR_ALCOHOL_FRECUENTE])
    out.loc[out.consumo_alcohol_12m == 0, "consumo_frecuente"] = 0

    out["consumo_30d"] = _si_no(out[cfg.VAR_ALCOHOL_30D])
    out.loc[out.consumo_alcohol_12m == 0, "consumo_30d"] = 0

    # ── Criterios, no conteo crudo de ítems ──────────────────────────
    # Dentro del bloque hay saltos del tipo "si responde Sí, salta la
    # siguiente": QS721->QS722 y QS723->QS724->QS725 solo se preguntan a quien
    # respondió NO a la anterior, porque el criterio ya quedó satisfecho.
    # Sumar ítems en crudo penalizaría justo a los casos más graves (su NaN
    # es un "ya cumplió", no un "no cumple"). Por eso cada criterio se evalúa
    # con lógica OR sobre su grupo de ítems.
    # El caso inverso es QS714->QS715, que solo se pregunta si QS714 == Sí.
    def _criterio(items: list[str]) -> pd.Series:
        return out[items].eq(1).any(axis=1)

    llego_n1 = out.consumo_frecuente == 1
    criterios_n1 = {
        "abuso_actividades": _criterio(["QS713"]),   # dificultó sus actividades
        "abuso_social": _criterio(["QS715"]),        # siguió pese a problemas con otros
        "abuso_riesgo": _criterio(["QS716"]),        # bajo los efectos en situación de riesgo
        "abuso_legal": _criterio(["QS717"]),         # detenido por orden público / manejar
    }
    out["n_criterios_abuso"] = (
        pd.concat(criterios_n1.values(), axis=1).sum(axis=1).astype(float).where(llego_n1, 0.0)
    )
    out["alcohol_problematico"] = (out.n_criterios_abuso >= 2).astype("Float64")

    criterios_n2 = {
        "dep_deseo": _criterio(["QS719"]),                     # deseo irresistible
        "dep_tolerancia": _criterio(["QS720"]),                # necesitó más cantidad
        "dep_abstinencia": _criterio(["QS721", "QS722"]),      # síntomas de abstinencia
        "dep_mas_de_lo_previsto": _criterio(["QS723", "QS724", "QS725"]),
        "dep_no_pudo_reducir": _criterio(["QS726"]),
        "dep_tiempo": _criterio(["QS727"]),                    # tiempo bebiendo/recuperándose
        "dep_abandono_actividades": _criterio(["QS728"]),
        "dep_pese_a_dano": _criterio(["QS729"]),
    }
    llego_n2 = out[cfg.ITEMS_DEPENDENCIA_N1].eq(1).any(axis=1)
    out["n_criterios_dependencia"] = (
        pd.concat(criterios_n2.values(), axis=1).sum(axis=1).astype(float).where(llego_n2, 0.0)
    )
    out["alcohol_dependencia"] = (out.n_criterios_dependencia >= 3).astype("Float64")

    sin_dato = out.consumo_frecuente.isna()
    out.loc[sin_dato, ["n_criterios_abuso", "alcohol_problematico",
                       "n_criterios_dependencia", "alcohol_dependencia"]] = np.nan

    out["alcohol_categoria"] = pd.Categorical(
        np.select(
            [_cond(out.alcohol_problematico == 1), _cond(out.consumo_frecuente == 1),
             _cond(out.consumo_alcohol_12m == 1), _cond(out.consumo_alcohol_12m == 0)],
            ["Consumo problemático", "Frecuente sin problemas",
             "Ocasional", "No consumió en 12 meses"],
            default=None,
        ),
        categories=["No consumió en 12 meses", "Ocasional",
                    "Frecuente sin problemas", "Consumo problemático"],
        ordered=True,
    )

    _regla("consumo_alcohol_12m", "QS208 (1=Sí,2=No). Quien responde 'No' en QS206 (nunca bebió) se fija en 0.")
    _regla("consumo_frecuente", "QS209 = Sí (12 o más días en 12 meses). Quien no bebió en 12 meses se fija en 0.")
    _regla("n_criterios_abuso",
           "Número de criterios de abuso satisfechos (0-4), evaluados con lógica OR sobre "
           "sus ítems: actividades (QS713), social (QS715), riesgo (QS716), legal (QS717). "
           "Filtrado por QS209==1; quien no llegó al bloque = 0 (no aplica -> 0).")
    _regla("alcohol_problematico", "1 si n_criterios_abuso >= 2.")
    _regla("n_criterios_dependencia",
           "Número de criterios de dependencia satisfechos (0-8) sobre QS719-QS729, "
           "agrupando por criterio y no por ítem: abstinencia = QS721 o QS722; "
           "'más de lo previsto' = QS723 o QS724 o QS725. Esta agrupación es necesaria "
           "porque el cuestionario salta la pregunta siguiente cuando la anterior fue 'Sí' "
           "(el criterio ya quedó satisfecho): contar ítems en crudo penalizaría a los "
           "casos más graves. Filtrado por alguna de QS713-717 == Sí; quien no llegó = 0.")
    _regla("alcohol_dependencia", "1 si n_criterios_dependencia >= 3.")
    log.info("Alcohol: %s", out.alcohol_categoria.value_counts().to_dict())
    return out


def construir_tabaco(df: pd.DataFrame) -> pd.DataFrame:
    """Construye el bloque de tabaco (QS200 -> QS201 -> QS202)."""
    out = df.copy()
    out["fuma_12m"] = _si_no(out[cfg.VAR_TABACO_12M])
    out["fuma_30d"] = _si_no(out[cfg.VAR_TABACO_30D])
    out.loc[out.fuma_12m == 0, "fuma_30d"] = 0
    out["fuma_diario"] = _si_no(out[cfg.VAR_TABACO_DIARIO])
    out.loc[out.fuma_30d == 0, "fuma_diario"] = 0

    out["tabaco_categoria"] = pd.Categorical(
        np.select(
            [_cond(out.fuma_diario == 1), _cond(out.fuma_30d == 1),
             _cond(out.fuma_12m == 1), _cond(out.fuma_12m == 0)],
            ["Fumador diario", "Fumador ocasional", "Fumó en 12 meses", "No fumó"],
            default=None,
        ),
        categories=["No fumó", "Fumó en 12 meses", "Fumador ocasional", "Fumador diario"],
        ordered=True,
    )
    _regla("fuma_12m", "QS200 = Sí.")
    _regla("fuma_30d", "QS201 = Sí; quien no fumó en 12 meses se fija en 0 (no aplica -> 0).")
    _regla("fuma_diario", "QS202 = Sí; quien no fumó en 30 días se fija en 0.")
    return out


# ─────────────────────────────────────────────────────────────────────
# 4. SOCIAL — VIOLENCIA DE PAREJA
# ─────────────────────────────────────────────────────────────────────


def construir_violencia(df: pd.DataFrame) -> pd.DataFrame:
    """Construye el bloque de violencia física de pareja.

    ``QS710`` y ``QS711`` solo se preguntan a quien tuvo pareja en los últimos
    12 meses (``QS709 == 1``). Quien no tuvo pareja **no** es un "0 de
    violencia": es una subpoblación distinta, y así se codifica.

    Sobre ``QS711``: el diccionario del INEI etiqueta 8 y 9 donde los datos
    graban 3 y 4. Se usa la escala ordinal 1-4 de ``QS710``, su pregunta
    gemela, y se conservan los 33 casos severos.
    """
    out = df.copy()

    out["estado_pareja"] = pd.Categorical(
        out[cfg.VAR_TUVO_PAREJA].map({1: "Con pareja", 2: "Sin pareja"}),
        categories=["Sin pareja", "Con pareja"],
    )
    con_pareja = out[cfg.VAR_TUVO_PAREJA].eq(1)
    out["tuvo_pareja"] = _si_no(out[cfg.VAR_TUVO_PAREJA])

    golpe = out[cfg.VAR_VIOLENCIA_GOLPE].where(con_pareja)
    objeto = out[cfg.VAR_VIOLENCIA_OBJETO].where(con_pareja)

    out["violencia_fisica"] = ((golpe > 1) | (objeto > 1)).astype("Float64").where(con_pareja)
    out["violencia_max"] = pd.concat([golpe, objeto], axis=1).max(axis=1)
    out["violencia_severidad"] = pd.Categorical(
        out.violencia_max.map(cfg.ESCALA_VIOLENCIA),
        categories=list(cfg.ESCALA_VIOLENCIA.values()), ordered=True,
    )
    out["violencia_objeto"] = (objeto > 1).astype("Float64").where(con_pareja)

    _regla("estado_pareja", "QS709: 1=Con pareja, 2=Sin pareja. Define la SUBPOBLACIÓN del análisis de violencia.")
    _regla("violencia_fisica",
           "1 si QS710 > 1 o QS711 > 1 (cualquier frecuencia distinta de 'Nunca'). "
           "Solo definida en la subpoblación con pareja; NaN para quien no tuvo pareja "
           "(no es un 0). QS711 se lee en escala 1-4 pese a que el diccionario del "
           "INEI etiqueta 8 y 9.")
    _regla("violencia_severidad", "Máximo de QS710 y QS711 en escala Nunca / Rara vez / A veces / A menudo.")

    n = int(con_pareja.sum())
    log.info("Violencia: subpoblación con pareja = %s; prevalencia = %.2f%%",
             f"{n:,}", out.violencia_fisica.mean() * 100)
    return out


# ─────────────────────────────────────────────────────────────────────
# 5. CLÍNICAS
# ─────────────────────────────────────────────────────────────────────


def construir_clinicas(df: pd.DataFrame) -> pd.DataFrame:
    """Construye IMC, obesidad, hipertensión medida, diabetes y comorbilidad."""
    out = df.copy()

    out["peso_kg"] = out[cfg.VAR_PESO_KG]
    out["talla_cm"] = out[cfg.VAR_TALLA_CM]
    out["perimetro_abdominal"] = out[cfg.VAR_PERIMETRO_ABD]

    out["imc"] = out.peso_kg / (out.talla_cm / 100) ** 2
    out.loc[(out.imc < 12) | (out.imc > 70), "imc"] = np.nan  # rangos implausibles

    out["imc_categoria"] = pd.Categorical(
        np.select(
            [_cond(out.imc < 18.5), _cond(out.imc < cfg.IMC_SOBREPESO),
             _cond(out.imc < cfg.IMC_OBESIDAD), _cond(out.imc >= cfg.IMC_OBESIDAD)],
            ["Bajo peso", "Normal", "Sobrepeso", "Obesidad"], default=None,
        ),
        categories=["Bajo peso", "Normal", "Sobrepeso", "Obesidad"], ordered=True,
    )
    out["obesidad"] = (out.imc >= cfg.IMC_OBESIDAD).astype("Float64").where(out.imc.notna())

    umbral = out[cfg.VAR_SEXO].map(cfg.PERIMETRO_RIESGO)
    out["obesidad_abdominal"] = (out.perimetro_abdominal >= umbral).astype("Float64").where(
        out.perimetro_abdominal.notna() & umbral.notna()
    )

    sis = out[cfg.PRESION_SISTOLICA].mean(axis=1)
    dia = out[cfg.PRESION_DIASTOLICA].mean(axis=1)
    out["presion_sistolica"] = sis
    out["presion_diastolica"] = dia
    out["hta_medida"] = ((sis >= cfg.HTA_SISTOLICA) | (dia >= cfg.HTA_DIASTOLICA)).astype(
        "Float64"
    ).where(sis.notna() & dia.notna())

    out["hta_dx"] = _si_no(out[cfg.VAR_HTA_DX])
    out["diabetes_dx"] = _si_no(out[cfg.VAR_DIABETES_DX])

    out["n_cronicas"] = (
        out[["hta_dx", "diabetes_dx", "obesidad"]].sum(axis=1, min_count=1)
    )
    out["tiene_cronica"] = (out.n_cronicas >= 1).astype("Float64").where(out.n_cronicas.notna())

    _regla("imc", "peso_kg / (talla_cm/100)^2, tras convertir a NaN los códigos de no-medición (>=900). "
                  "Valores fuera de [12, 70] se descartan por implausibles.")
    _regla("obesidad", f"IMC >= {cfg.IMC_OBESIDAD}.")
    _regla("obesidad_abdominal", "Perímetro abdominal >= 102 cm en hombres, >= 88 cm en mujeres.")
    _regla("hta_medida", f"Promedio de las dos tomas: sistólica >= {cfg.HTA_SISTOLICA} o diastólica >= {cfg.HTA_DIASTOLICA} mmHg.")
    _regla("hta_dx", "QS102 = Sí (diagnóstico autorreportado de hipertensión).")
    _regla("diabetes_dx", "QS109 = Sí (diagnóstico autorreportado de diabetes).")
    _regla("n_cronicas", "Suma de hta_dx, diabetes_dx y obesidad (0-3).")
    return out


# ─────────────────────────────────────────────────────────────────────
# 6. ATENCIÓN EN SALUD MENTAL
# ─────────────────────────────────────────────────────────────────────


def construir_atencion(df: pd.DataFrame) -> pd.DataFrame:
    """Construye el bloque de atención y la brecha de atención.

    ``brecha_atencion`` solo está definida para quienes tienen
    ``depresion_bin == 1``: es la proporción de personas con síntomas
    moderados o graves que **no** recibió atención profesional.
    """
    out = df.copy()

    out["recibio_tratamiento_sm"] = _si_no(out[cfg.VAR_TRATAMIENTO_SM])
    con_depresion = _cond(out.depresion_bin == 1)
    out["brecha_atencion"] = (1 - out.recibio_tratamiento_sm).where(con_depresion)

    lugares = [c for c in out.columns if c.startswith(cfg.PREFIJO_LUGAR_ATENCION)]
    if lugares:
        out["n_lugares_atencion"] = out[lugares].sum(axis=1, min_count=1)

    _regla("recibio_tratamiento_sm",
           "QS707 = Sí (recibió tratamiento profesional por depresión/tristeza en 12 meses).")
    _regla("brecha_atencion",
           "1 - recibio_tratamiento_sm, calculada SOLO entre quienes tienen "
           "depresion_bin == 1. NaN para el resto.")

    con = out.depresion_bin == 1
    if con.any():
        log.info("Brecha de atención: %.1f%% de %s casos con depresión",
                 out.loc[con, "brecha_atencion"].mean() * 100, f"{int(con.sum()):,}")
    return out


# ─────────────────────────────────────────────────────────────────────
# 7. DISEÑO MUESTRAL
# ─────────────────────────────────────────────────────────────────────


def construir_diseno(df: pd.DataFrame) -> pd.DataFrame:
    """Añade las tres columnas del diseño muestral complejo, ya escaladas."""
    out = df.copy()
    out["peso"] = out[cfg.VAR_PESO] / cfg.ESCALA_PESO
    out["conglomerado"] = out[cfg.VAR_CONGLOMERADO]
    out["estrato"] = out[cfg.VAR_ESTRATO]
    out["tiene_peso"] = out.peso.notna().astype(int)

    _regla("peso", f"{cfg.VAR_PESO} / {cfg.ESCALA_PESO:,} (ficha técnica ENDES 2025, pág. 12). "
                   "Es un peso RELATIVO normalizado, no un factor de expansión: sirve para "
                   "proporciones y errores estándar, no para totales poblacionales.")
    _regla("conglomerado", f"{cfg.VAR_CONGLOMERADO} (UPM).")
    _regla("estrato", f"{cfg.VAR_ESTRATO}, proveniente de RECH0.")

    log.info("Diseño: %s conglomerados, %s estratos, suma de pesos = %.2f",
             f"{out.conglomerado.nunique():,}", out.estrato.nunique(), out.peso.sum())
    return out


# ─────────────────────────────────────────────────────────────────────
# 8. ORQUESTADOR
# ─────────────────────────────────────────────────────────────────────


def construir_todas(df: pd.DataFrame, etiquetas_departamento: dict) -> pd.DataFrame:
    """Aplica en orden todas las construcciones de variables."""
    out = construir_phq9(df)
    out = construir_sociodemograficas(out)
    out = construir_geografia(out, etiquetas_departamento)
    out = construir_alcohol(out)
    out = construir_tabaco(out)
    out = construir_violencia(out)
    out = construir_clinicas(out)
    out = construir_atencion(out)
    out = construir_diseno(out)
    log.info("Construcción completa: %s variables nuevas documentadas", len(REGLAS))
    return out
