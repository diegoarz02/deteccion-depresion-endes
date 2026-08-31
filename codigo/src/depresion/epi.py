"""Medidas de asociación epidemiológica: OR, RP, Mantel-Haenszel, confusión.

Todo devuelve estimadores con intervalo de confianza al 95 % y el n sobre el
que se calculó, para que ninguna cifra del informe quede sin denominador.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

log = logging.getLogger(__name__)

Z95 = 1.959963984540054


# ─────────────────────────────────────────────────────────────────────
# Tablas 2x2 y OR crudo
# ─────────────────────────────────────────────────────────────────────


def tabla_2x2(expuesto: pd.Series, desenlace: pd.Series) -> pd.DataFrame:
    """Construye la tabla 2×2 clásica con expuesto en filas.

    Returns
    -------
    pandas.DataFrame
        Filas: No expuesto / Expuesto. Columnas: Sin desenlace / Con desenlace.
    """
    d = pd.DataFrame({"e": expuesto, "y": desenlace}).dropna()
    t = pd.crosstab(d.e.astype(float), d.y.astype(float))
    for i in (0.0, 1.0):
        if i not in t.index:
            t.loc[i] = 0
        if i not in t.columns:
            t[i] = 0
    t = t.sort_index().sort_index(axis=1)
    t.index = ["No expuesto", "Expuesto"]
    t.columns = ["Sin desenlace", "Con desenlace"]
    return t


def odds_ratio(
    expuesto: pd.Series, desenlace: pd.Series, correccion_haldane: bool = True
) -> dict:
    """Calcula el OR crudo con IC 95 % por el método de Woolf.

    Parameters
    ----------
    expuesto, desenlace : pandas.Series
        Variables binarias (0/1). Los NaN se descartan por pares.
    correccion_haldane : bool, default True
        Si alguna celda es cero, suma 0,5 a todas (corrección de
        Haldane-Anscombe) para que el OR no sea infinito. Se reporta.

    Returns
    -------
    dict
        ``or``, ``ic_inf``, ``ic_sup``, ``p``, ``n``, ``celdas``,
        ``celda_minima`` y ``advertencia``.
    """
    t = tabla_2x2(expuesto, desenlace)
    a, b = t.iloc[1, 1], t.iloc[1, 0]   # expuestos con y sin desenlace
    c, d = t.iloc[0, 1], t.iloc[0, 0]   # no expuestos con y sin desenlace
    n = int(t.values.sum())
    minima = int(min(a, b, c, d))

    advertencia = ""
    if minima == 0 and correccion_haldane:
        a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
        advertencia = "Celda con cero: se aplicó corrección de Haldane-Anscombe (+0,5)"
    elif minima < 10:
        advertencia = f"Celda mínima n={minima} (<10): estimador inestable"

    orr = (a * d) / (b * c)
    se = np.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    li, ls = np.exp(np.log(orr) - Z95 * se), np.exp(np.log(orr) + Z95 * se)

    tabla = np.array([[t.iloc[1, 1], t.iloc[1, 0]], [t.iloc[0, 1], t.iloc[0, 0]]])
    try:
        p = stats.chi2_contingency(tabla)[1] if minima >= 5 else stats.fisher_exact(tabla)[1]
    except ValueError:
        p = np.nan

    return {"or": orr, "ic_inf": li, "ic_sup": ls, "p": p, "n": n,
            "celdas": [int(x) for x in tabla.ravel()], "celda_minima": minima,
            "advertencia": advertencia}


def razon_prevalencias(expuesto: pd.Series, desenlace: pd.Series) -> dict:
    """Estima la razón de prevalencias por Poisson con varianza robusta.

    En estudios transversales el OR sobreestima la RP cuando la prevalencia es
    alta. Con prevalencia baja (aquí ~7 %) ambos deben parecerse; comprobarlo
    numéricamente es un punto de rigor, no un trámite.

    La regresión de Poisson con errores estándar robustos (sandwich) es el
    método recomendado frente a la log-binomial, que a menudo no converge.

    Returns
    -------
    dict
        ``rp``, ``ic_inf``, ``ic_sup``, ``p`` y ``n``.
    """
    d = pd.DataFrame({"e": expuesto, "y": desenlace}).dropna().astype(float)
    if d.empty or d.e.nunique() < 2:
        return {"rp": np.nan, "ic_inf": np.nan, "ic_sup": np.nan, "p": np.nan, "n": len(d)}
    X = sm.add_constant(d[["e"]])
    mod = sm.GLM(d.y, X, family=sm.families.Poisson()).fit(cov_type="HC0")
    b, se = mod.params["e"], mod.bse["e"]
    return {"rp": np.exp(b), "ic_inf": np.exp(b - Z95 * se), "ic_sup": np.exp(b + Z95 * se),
            "p": mod.pvalues["e"], "n": len(d)}


# ─────────────────────────────────────────────────────────────────────
# Estratificación y Mantel-Haenszel
# ─────────────────────────────────────────────────────────────────────


def mantel_haenszel(
    expuesto: pd.Series, desenlace: pd.Series, estrato: pd.Series
) -> dict:
    """Calcula el OR de Mantel-Haenszel ajustado por un estrato.

    Devuelve además la prueba de homogeneidad de Breslow-Day, que contrasta si
    el OR es el mismo en todos los estratos. Si se rechaza, hay **modificación
    de efecto** y no procede reportar un único OR ajustado: hay que reportar
    los OR por estrato.

    Returns
    -------
    dict
        ``or_mh``, su IC 95 %, el p de homogeneidad, el OR crudo, el cambio
        porcentual entre crudo y ajustado y el veredicto sobre confusión.
    """
    d = pd.DataFrame({"e": expuesto, "y": desenlace, "s": estrato}).dropna()
    tablas, por_estrato = [], []
    for k, g in d.groupby("s"):
        t = tabla_2x2(g.e, g.y)
        arr = np.array([[t.iloc[1, 1], t.iloc[1, 0]], [t.iloc[0, 1], t.iloc[0, 0]]])
        if arr.min() == 0 or arr.sum() < 20:
            continue
        tablas.append(arr)
        r = odds_ratio(g.e, g.y)
        por_estrato.append({"estrato": str(k), "n": r["n"], "or": r["or"],
                            "ic_inf": r["ic_inf"], "ic_sup": r["ic_sup"], "p": r["p"]})

    if len(tablas) < 2:
        return {"or_mh": np.nan, "error": "menos de 2 estratos utilizables"}

    tab = sm.stats.StratifiedTable([t.T for t in tablas])
    crudo = odds_ratio(d.e, d.y)["or"]
    or_mh = tab.oddsratio_pooled
    cambio = (crudo - or_mh) / or_mh * 100
    li, ls = tab.oddsratio_pooled_confint()
    p_homog = tab.test_equal_odds().pvalue

    return {
        "or_crudo": crudo, "or_mh": or_mh, "ic_inf": li, "ic_sup": ls,
        "p_homogeneidad": p_homog, "cambio_pct": cambio,
        "hay_confusion": abs(cambio) >= 10,
        "hay_interaccion": p_homog < 0.05,
        "n_estratos": len(tablas), "por_estrato": por_estrato,
        "veredicto": (
            "Modificación de efecto: reportar OR por estrato, no un OR único"
            if p_homog < 0.05 else
            ("Confusión: el ajuste cambia el estimador ≥10 %" if abs(cambio) >= 10
             else "Sin confusión relevante (cambio <10 %)")
        ),
    }


def evaluar_confusion(
    df: pd.DataFrame, exposicion: str, desenlace: str, candidatos: list[str]
) -> pd.DataFrame:
    """Evalúa cada candidato a confusor por el criterio del cambio del 10 %.

    El criterio: si el OR crudo y el OR ajustado por la variable difieren en
    10 % o más, la variable confunde la asociación y debe entrar al modelo.

    ⚠️ Este criterio **no sustituye al DAG**. Una variable puede cambiar el
    estimador ≥10 % por ser mediadora o colisionadora, y ajustarla entonces
    empeora la estimación. El cambio del 10 % informa; el DAG decide.

    Returns
    -------
    pandas.DataFrame
        Una fila por candidato con OR crudo, OR de Mantel-Haenszel, cambio
        porcentual, p de homogeneidad y veredicto.
    """
    filas = []
    for c in candidatos:
        if c not in df.columns:
            continue
        r = mantel_haenszel(df[exposicion], df[desenlace], df[c].astype(str))
        if "error" in r:
            filas.append({"candidato": c, "veredicto": r["error"]})
            continue
        filas.append({
            "candidato": c, "or_crudo": r["or_crudo"], "or_ajustado": r["or_mh"],
            "ic_inf": r["ic_inf"], "ic_sup": r["ic_sup"],
            "cambio_pct": r["cambio_pct"], "p_homogeneidad": r["p_homogeneidad"],
            "confunde": r["hay_confusion"], "modifica_efecto": r["hay_interaccion"],
            "veredicto": r["veredicto"],
        })
    return pd.DataFrame(filas)


# ─────────────────────────────────────────────────────────────────────
# Comparaciones múltiples
# ─────────────────────────────────────────────────────────────────────


def ajustar_p(p: pd.Series, metodo: str = "fdr_bh") -> pd.Series:
    """Ajusta valores p por comparaciones múltiples.

    Parameters
    ----------
    p : pandas.Series
        Valores p sin ajustar.
    metodo : str, default "fdr_bh"
        ``"fdr_bh"`` (Benjamini-Hochberg) o ``"bonferroni"``.
    """
    from statsmodels.stats.multitest import multipletests

    val = p.dropna()
    out = pd.Series(np.nan, index=p.index, dtype=float)
    if len(val):
        out.loc[val.index] = multipletests(val.values, method=metodo)[1]
    return out


# ─────────────────────────────────────────────────────────────────────
# Multicolinealidad
# ─────────────────────────────────────────────────────────────────────


def cramers_v(a: pd.Series, b: pd.Series) -> float:
    """Calcula la V de Cramér entre dos variables categóricas, con corrección."""
    d = pd.DataFrame({"a": a, "b": b}).dropna()
    if d.empty or d.a.nunique() < 2 or d.b.nunique() < 2:
        return np.nan
    t = pd.crosstab(d.a, d.b)
    chi2 = stats.chi2_contingency(t)[0]
    n = t.values.sum()
    phi2 = max(0, chi2 / n - (t.shape[0] - 1) * (t.shape[1] - 1) / (n - 1))
    r = t.shape[0] - (t.shape[0] - 1) ** 2 / (n - 1)
    k = t.shape[1] - (t.shape[1] - 1) ** 2 / (n - 1)
    denom = min(r - 1, k - 1)
    return np.sqrt(phi2 / denom) if denom > 0 else np.nan


def vif(df: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    """Calcula el GVIF de cada variable, tratando los factores como un bloque.

    El VIF corriente sobre dummies es engañoso: los indicadores de un mismo
    factor están correlacionados entre sí **por construcción** (suman uno), de
    modo que un factor de seis niveles produce VIF de 8-15 sin que exista
    ningún problema real de colinealidad.

    Se usa el GVIF de Fox y Monette (1992), que evalúa el bloque completo de
    dummies de cada variable, y su versión comparable ``GVIF^(1/(2·gl))``, que
    se lee en la misma escala que ``sqrt(VIF)``: por encima de 2,24 equivale a
    un VIF de 5, y por encima de 3,16 a un VIF de 10.

    Parameters
    ----------
    df : pandas.DataFrame
        Datos con las variables del modelo.
    variables : list of str
        Variables a evaluar. Se descartan por lista las filas con faltantes,
        así que no deben mezclarse variables definidas en subpoblaciones
        distintas: una variable constante tras el descarte da un GVIF absurdo.

    Returns
    -------
    pandas.DataFrame
        Una fila por variable con ``gvif``, grados de libertad, el valor
        comparable y el diagnóstico.
    """
    d = df[variables].dropna()
    bloques: dict[str, list[str]] = {}
    piezas = []
    for v in variables:
        col = d[[v]]
        dm = pd.get_dummies(col, columns=[v], drop_first=True).astype(float) \
            if (col[v].dtype == object or isinstance(col[v].dtype, pd.CategoricalDtype)
                or col[v].nunique() > 2) else col.astype(float)
        bloques[v] = list(dm.columns)
        piezas.append(dm)
    X = pd.concat(piezas, axis=1)

    constantes = [v for v, cs in bloques.items() if all(X[c].nunique() <= 1 for c in cs)]
    filas = []
    R = np.corrcoef(X.values, rowvar=False)
    det_total = np.linalg.det(R)
    for v, cs in bloques.items():
        if v in constantes:
            filas.append({"variable": v, "gl": len(cs), "gvif": np.nan,
                          "gvif_comparable": np.nan,
                          "diagnostico": "Constante tras descartar faltantes: no evaluable"})
            continue
        idx = [X.columns.get_loc(c) for c in cs]
        otros = [i for i in range(X.shape[1]) if i not in idx]
        det_v = np.linalg.det(R[np.ix_(idx, idx)])
        det_o = np.linalg.det(R[np.ix_(otros, otros)]) if otros else 1.0
        g = (det_v * det_o) / det_total if det_total > 0 else np.nan
        filas.append({"variable": v, "gl": len(cs), "gvif": g,
                      "gvif_comparable": g ** (1 / (2 * len(cs))) if g and g > 0 else np.nan})

    out = pd.DataFrame(filas)
    out["diagnostico"] = out.diagnostico if "diagnostico" in out else ""
    out["diagnostico"] = np.select(
        [out.gvif_comparable.isna(), out.gvif_comparable >= 3.16, out.gvif_comparable >= 2.24],
        [out.get("diagnostico", "No evaluable"), "Colinealidad grave", "Colinealidad moderada"],
        default="Aceptable",
    )
    if constantes:
        log.warning("Variables constantes tras el descarte por lista: %s. "
                    "Probablemente estén definidas en una subpoblación distinta.",
                    constantes)
    return out.sort_values("gvif_comparable", ascending=False).reset_index(drop=True)


def formato_ic(est: float, li: float, ls: float, dec: int = 2) -> str:
    """Formatea un estimador con su intervalo: ``1,85 (1,42 – 2,41)``."""
    if pd.isna(est):
        return "—"
    return f"{est:.{dec}f} ({li:.{dec}f} – {ls:.{dec}f})"


def formato_p(p: float) -> str:
    """Formatea un valor p según convención de publicación."""
    if pd.isna(p):
        return "—"
    if p < 0.001:
        return "<0,001"
    return f"{p:.3f}".replace(".", ",")
