"""Diseño muestral complejo: estimación de prevalencias, medias y efecto de diseño.

Envoltorio sobre ``svy`` que fija de una vez las tres decisiones que este
proyecto tomó sobre el diseño de ENDES:

1. **Estratos con un solo conglomerado.** Hay 18 (7,5 % de los estratos, que
   afectan al 0,49 % de las filas). Sin tratarlos, la varianza no se puede
   estimar. Se usa el centrado en la media general, equivalente a
   ``options(survey.lonely.psu = "adjust")`` de R, que es la opción estándar
   y citable. Las cinco estrategias disponibles dan el mismo resultado hasta
   el cuarto decimal, así que la elección no altera conclusiones.

2. **Efecto de diseño con referencia "wr"** (muestreo aleatorio simple con
   reemplazo). La variante ``wor`` aplica una corrección por población finita
   que supone que la suma de pesos es el tamaño poblacional. Aquí el
   ponderador es relativo (suma 36 173), así que esa corrección infla el deff
   por un factor 6 y produce valores imposibles (18,8 en lugar de 3,1).

3. **Subpoblaciones con ``where``**, nunca filtrando los datos antes de
   declarar el diseño: filtrar deja estratos y conglomerados vacíos y rompe
   el cálculo de varianza.
"""

from __future__ import annotations

import logging
import warnings

import pandas as pd
import polars as pl
import svy

from . import config as cfg

log = logging.getLogger(__name__)

warnings.filterwarnings("ignore", message=".*samplics is archived.*")

# Estrategia de tratamiento de estratos con un solo conglomerado.
ESTRATEGIA_SINGLETON = "center"

# Referencia del efecto de diseño. Ver punto 2 del docstring del módulo.
REFERENCIA_DEFF = "wr"


def preparar(df: pd.DataFrame, columnas: list[str] | None = None) -> pl.DataFrame:
    """Convierte el DataFrame de pandas a polars, con las categóricas como texto.

    ``svy`` trabaja sobre polars y no acepta el dtype ``category`` de pandas
    ni los enteros nulables, de modo que se normalizan aquí.

    Parameters
    ----------
    df : pandas.DataFrame
        Datos de entrada.
    columnas : list of str, optional
        Subconjunto de columnas a conservar. Por defecto, todas.

    Returns
    -------
    polars.DataFrame
    """
    d = df if columnas is None else df[list(dict.fromkeys(columnas))]
    d = d.copy()
    for c in d.columns:
        if isinstance(d[c].dtype, pd.CategoricalDtype) or d[c].dtype == object:
            d[c] = d[c].astype(str).replace({"nan": None, "<NA>": None, "None": None})
        elif str(d[c].dtype).startswith(("Int", "Float", "boolean")):
            d[c] = d[c].astype("float64")
    return pl.from_pandas(d)


def crear_diseno(df: pd.DataFrame, columnas: list[str] | None = None):
    """Declara el objeto de diseño muestral con los singletons ya tratados.

    Parameters
    ----------
    df : pandas.DataFrame
        Debe contener ``peso``, ``conglomerado`` y ``estrato``.
    columnas : list of str, optional
        Columnas a incluir además de las tres del diseño.

    Returns
    -------
    svy.Sample
        Muestra lista para estimar, con los estratos de un solo conglomerado
        resueltos.
    """
    base = ["peso", "conglomerado", "estrato"]
    cols = base + [c for c in (columnas or df.columns) if c not in base]
    pf = preparar(df, cols)

    s = svy.Sample(pf, svy.Design(stratum="estrato", psu="conglomerado", wgt="peso"))
    n_sing = s.singleton.count
    if n_sing:
        s = getattr(s.singleton, ESTRATEGIA_SINGLETON)()
        log.info("Diseño: %s estratos con un solo conglomerado tratados con '%s'",
                 n_sing, ESTRATEGIA_SINGLETON)
    log.info("Diseño declarado: n=%s, %s conglomerados, %s estratos",
             f"{len(pf):,}", f"{s.n_psus:,}", s.n_strata)
    return s


def _a_pandas(est) -> pd.DataFrame:
    """Convierte un ``Estimate`` de svy a un DataFrame de pandas."""
    return est.to_polars().to_pandas()


def prevalencia(
    diseno,
    variable: str = "depresion_bin",
    por: str | list[str] | None = None,
    donde=None,
    con_deff: bool = True,
) -> pd.DataFrame:
    """Estima una prevalencia ponderada con su intervalo de confianza al 95 %.

    Parameters
    ----------
    diseno : svy.Sample
        Objeto devuelto por :func:`crear_diseno`.
    variable : str, default "depresion_bin"
        Variable binaria cuya proporción se estima.
    por : str or list of str, optional
        Variable(s) de desagregación.
    donde : optional
        Expresión de subpoblación (``svy.col(...) == ...``). Se pasa a ``where``
        en lugar de filtrar los datos.
    con_deff : bool, default True
        Si se reporta el efecto de diseño.

    Returns
    -------
    pandas.DataFrame
        Columnas: categoría(s), ``est``, ``se``, ``lci``, ``uci``, ``cv`` y,
        si se pidió, ``deff``. Solo la fila de la categoría positiva (1).
    """
    # drop_nulls descarta los faltantes de la variable de desagregación. La
    # estimación queda condicionada a los casos con esa variable observada,
    # que es lo correcto para una prevalencia por subgrupo: la categoría
    # "faltante" no es un subgrupo poblacional.
    r = diseno.estimation.prop(
        variable, by=por, where=donde,
        deff=REFERENCIA_DEFF if con_deff else None,
        drop_nulls=True,
    )
    out = _a_pandas(r)
    if variable in out.columns:
        out = out[out[variable].astype(str).isin(["1", "1.0", "True"])].drop(columns=variable)
    for c in ("est", "se", "lci", "uci"):
        if c in out.columns:
            out[c] = out[c] * 100
    return out.reset_index(drop=True)


def media(
    diseno, variable: str, por: str | list[str] | None = None, donde=None,
    con_deff: bool = True,
) -> pd.DataFrame:
    """Estima una media ponderada con su intervalo de confianza al 95 %."""
    r = diseno.estimation.mean(
        variable, by=por, where=donde,
        deff=REFERENCIA_DEFF if con_deff else None,
        drop_nulls=True,
    )
    return _a_pandas(r).reset_index(drop=True)


def tamano_efectivo(n: int, deff: float) -> float:
    """Calcula el tamaño de muestra efectivo ``n / deff``.

    Un deff de 3 significa que 30 000 encuestas informan como 10 000 aleatorias
    simples. Reportarlo es parte del oficio en encuestas complejas.
    """
    return n / deff if deff and deff > 0 else float("nan")


def tabla_prevalencias(
    df: pd.DataFrame,
    variables: list[str],
    desenlace: str = "depresion_bin",
    etiquetas: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Construye la tabla de prevalencias ponderadas, nacional y por subgrupos.

    Parameters
    ----------
    df : pandas.DataFrame
        Población de análisis.
    variables : list of str
        Variables de desagregación (sexo, área, región…).
    desenlace : str, default "depresion_bin"
        Variable binaria del desenlace.
    etiquetas : dict, optional
        Nombre de variable -> etiqueta legible para la tabla.

    Returns
    -------
    pandas.DataFrame
        Una fila por categoría, con n, prevalencia ponderada, IC 95 % y deff.
    """
    etiquetas = etiquetas or {}
    d = df.dropna(subset=[desenlace]).copy()
    diseno = crear_diseno(d, [desenlace, *variables])

    filas = []
    nac = prevalencia(diseno, desenlace)
    filas.append({
        "variable": "Total", "categoria": "Nacional", "n": len(d),
        "prevalencia": nac.est[0], "ic_inf": nac.lci[0], "ic_sup": nac.uci[0],
        "cv": nac["cv (%)"][0] if "cv (%)" in nac else None,
        "deff": nac.deff[0] if "deff" in nac else None,
    })

    for v in variables:
        sub = prevalencia(diseno, desenlace, por=v)
        conteo = d[v].astype(str).value_counts()
        for _, r in sub.iterrows():
            cat = str(r[v])
            if cat in ("None", "nan", "<NA>"):
                continue
            filas.append({
                "variable": etiquetas.get(v, v), "categoria": cat,
                "n": int(conteo.get(cat, 0)),
                "prevalencia": r.est, "ic_inf": r.lci, "ic_sup": r.uci,
                "cv": r.get("cv (%)"), "deff": r.get("deff"),
            })
    out = pd.DataFrame(filas)
    out["ic_95"] = out.apply(lambda r: f"({r.ic_inf:.2f} – {r.ic_sup:.2f})", axis=1)
    return out


def resumen_diseno(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve la ficha del diseño muestral para la sección de métodos."""
    d = df.dropna(subset=["peso"])
    diseno = crear_diseno(d, ["depresion_bin"])
    prev = prevalencia(diseno, "depresion_bin")
    deff = float(prev.deff[0]) if "deff" in prev else float("nan")
    return pd.DataFrame([
        {"elemento": "Tamaño de muestra analítica", "valor": f"{len(d):,}"},
        {"elemento": "Conglomerados (UPM)", "valor": f"{d.conglomerado.nunique():,}"},
        {"elemento": "Estratos", "valor": f"{d.estrato.nunique():,}"},
        {"elemento": "Estratos con un solo conglomerado", "valor": "18 (tratados con centrado)"},
        {"elemento": "Ponderador", "valor": f"{cfg.VAR_PESO} / {cfg.ESCALA_PESO:,}"},
        {"elemento": "Suma de pesos escalados", "valor": f"{d.peso.sum():,.1f}"},
        {"elemento": "¿Es factor de expansión?", "valor": "No — ponderador relativo"},
        {"elemento": "Efecto de diseño (deff, ref. wr)", "valor": f"{deff:.3f}"},
        {"elemento": "Tamaño de muestra efectivo", "valor": f"{tamano_efectivo(len(d), deff):,.0f}"},
        {"elemento": "Método de varianza", "valor": "Linealización de Taylor"},
    ])
