"""Batería de diagnósticos de supuestos para ANOVA y regresión.

Cada función devuelve, además del estadístico, un veredicto legible y la
alternativa robusta que corresponde si el supuesto falla. La política del
proyecto es **declarar el problema y usar la alternativa**, nunca ignorarlo.

Nota sobre el tamaño muestral: con N ≈ 30 000, las pruebas de bondad de ajuste
rechazan cualquier hipótesis nula por desviaciones triviales. Por eso todas las
funciones acompañan el valor p con un **tamaño de efecto**, que es lo que
decide si la violación importa en la práctica.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy import stats

log = logging.getLogger(__name__)

SEMILLA = 42


# ─────────────────────────────────────────────────────────────────────
# Normalidad
# ─────────────────────────────────────────────────────────────────────


def normalidad(residuos: np.ndarray, n_submuestra: int = 5000) -> dict:
    """Evalúa normalidad con Shapiro-Wilk sobre submuestra y tamaño de efecto.

    Shapiro-Wilk no admite más de 5 000 observaciones y, con N grande, rechaza
    por desviaciones irrelevantes. Se acompaña de asimetría y curtosis, que sí
    dicen cuánto se aparta la distribución.

    Returns
    -------
    dict
        Estadístico, p, asimetría, curtosis y veredicto.
    """
    r = np.asarray(residuos)
    r = r[np.isfinite(r)]
    rng = np.random.default_rng(SEMILLA)
    sub = rng.choice(r, size=min(n_submuestra, len(r)), replace=False)
    W, p = stats.shapiro(sub)
    asim, curt = stats.skew(r), stats.kurtosis(r)
    grave = abs(asim) > 1 or abs(curt) > 3
    return {
        "prueba": f"Shapiro-Wilk (submuestra n={len(sub)})",
        "estadistico": W, "p": p, "asimetria": asim, "curtosis": curt,
        "cumple": p >= 0.05,
        "veredicto": (
            "Normalidad aceptable" if p >= 0.05 else
            ("Desviación GRAVE de la normalidad (|asimetría|>1 o |curtosis|>3): "
             "usar alternativa no paramétrica o transformación" if grave else
             "Rechaza normalidad, pero la desviación es leve: con N grande el "
             "teorema central del límite respalda la inferencia sobre los coeficientes")
        ),
    }


def qq_datos(residuos: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Devuelve los cuantiles teóricos y muestrales para un gráfico Q-Q."""
    r = np.sort(np.asarray(residuos)[np.isfinite(residuos)])
    teoricos = stats.norm.ppf((np.arange(1, len(r) + 1) - 0.5) / len(r))
    return teoricos, (r - r.mean()) / r.std()


# ─────────────────────────────────────────────────────────────────────
# Homocedasticidad
# ─────────────────────────────────────────────────────────────────────


def levene(df: pd.DataFrame, variable: str, grupo: str) -> dict:
    """Prueba de Levene (centrada en la mediana) para igualdad de varianzas."""
    grupos = [g[variable].dropna().values for _, g in df.groupby(grupo, observed=True)
              if g[variable].notna().sum() > 2]
    W, p = stats.levene(*grupos, center="median")
    varianzas = [float(np.var(g, ddof=1)) for g in grupos]
    razon = max(varianzas) / min(varianzas) if min(varianzas) > 0 else np.inf
    return {
        "prueba": "Levene (centrada en la mediana)", "estadistico": W, "p": p,
        "razon_varianzas": razon, "cumple": p >= 0.05,
        "veredicto": ("Varianzas homogéneas" if p >= 0.05 else
                      f"Heterocedasticidad (razón máx/mín = {razon:.2f}): usar ANOVA de Welch"),
    }


def breusch_pagan(modelo) -> dict:
    """Prueba de Breusch-Pagan de heterocedasticidad sobre un modelo ajustado."""
    from statsmodels.stats.diagnostic import het_breuschpagan

    lm, lm_p, f, f_p = het_breuschpagan(modelo.resid, modelo.model.exog)
    return {
        "prueba": "Breusch-Pagan", "estadistico": lm, "p": lm_p, "cumple": lm_p >= 0.05,
        "veredicto": ("Homocedasticidad aceptable" if lm_p >= 0.05 else
                      "Heterocedasticidad: usar errores estándar robustos HC3"),
    }


# ─────────────────────────────────────────────────────────────────────
# ANOVA y alternativas
# ─────────────────────────────────────────────────────────────────────


def anova_completo(df: pd.DataFrame, variable: str, grupo: str) -> dict:
    """Ejecuta ANOVA de un factor con verificación de supuestos y alternativas.

    Reporta las tres versiones —clásica, de Welch y Kruskal-Wallis— junto con
    los tamaños de efecto eta² y omega², y señala cuál es la conclusión válida
    según los supuestos que se cumplan.

    Parameters
    ----------
    df : pandas.DataFrame
    variable : str
        Variable dependiente continua.
    grupo : str
        Factor de agrupación.

    Returns
    -------
    dict
        Resultados de las tres pruebas, supuestos y veredicto final.
    """
    d = df[[variable, grupo]].dropna()
    grupos = [g[variable].values for _, g in d.groupby(grupo, observed=True) if len(g) > 2]
    k, n = len(grupos), len(d)

    F, p_anova = stats.f_oneway(*grupos)
    gran_media = d[variable].mean()
    ss_entre = sum(len(g) * (g.mean() - gran_media) ** 2 for g in grupos)
    ss_total = ((d[variable] - gran_media) ** 2).sum()
    ss_dentro = ss_total - ss_entre
    ms_dentro = ss_dentro / (n - k)
    eta2 = ss_entre / ss_total
    omega2 = (ss_entre - (k - 1) * ms_dentro) / (ss_total + ms_dentro)

    W_welch, p_welch = stats.f_oneway(*grupos) if k < 2 else _welch_anova(grupos)
    H, p_kw = stats.kruskal(*grupos)
    epsilon2 = (H - k + 1) / (n - k)

    lev = levene(d, variable, grupo)
    residuos = np.concatenate([g - g.mean() for g in grupos])
    norm = normalidad(residuos)

    if not lev["cumple"] and not norm["cumple"]:
        valido = "Kruskal-Wallis"
    elif not lev["cumple"]:
        valido = "ANOVA de Welch"
    else:
        valido = "ANOVA clásico"

    return {
        "variable": variable, "factor": grupo, "n": n, "k_grupos": k,
        "F": F, "p_anova": p_anova,
        "F_welch": W_welch, "p_welch": p_welch,
        "H_kruskal": H, "p_kruskal": p_kw,
        "eta2": eta2, "omega2": omega2, "epsilon2": epsilon2,
        "levene_p": lev["p"], "levene_cumple": lev["cumple"],
        "shapiro_p": norm["p"], "asimetria": norm["asimetria"], "curtosis": norm["curtosis"],
        "normalidad_cumple": norm["cumple"],
        "prueba_valida": valido,
        "magnitud_efecto": _magnitud(eta2),
        "veredicto": (
            f"Supuestos: homocedasticidad {'sí' if lev['cumple'] else 'NO'}, "
            f"normalidad {'sí' if norm['cumple'] else 'NO'}. "
            f"Se reporta {valido}. Tamaño de efecto η² = {eta2:.4f} ({_magnitud(eta2)})."
        ),
    }


def _welch_anova(grupos: list[np.ndarray]) -> tuple[float, float]:
    """ANOVA de Welch, que no asume igualdad de varianzas."""
    k = len(grupos)
    n = np.array([len(g) for g in grupos], dtype=float)
    m = np.array([g.mean() for g in grupos])
    v = np.array([g.var(ddof=1) for g in grupos])
    w = n / v
    m_pond = (w * m).sum() / w.sum()
    num = ((w * (m - m_pond) ** 2).sum()) / (k - 1)
    lam = (((1 - w / w.sum()) ** 2) / (n - 1)).sum()
    den = 1 + (2 * (k - 2) / (k**2 - 1)) * lam
    F = num / den
    gl2 = (k**2 - 1) / (3 * lam)
    return F, float(stats.f.sf(F, k - 1, gl2))


def _magnitud(eta2: float) -> str:
    """Clasifica el tamaño de efecto según las referencias de Cohen."""
    if eta2 < 0.01:
        return "insignificante"
    if eta2 < 0.06:
        return "pequeño"
    if eta2 < 0.14:
        return "mediano"
    return "grande"


def games_howell(df: pd.DataFrame, variable: str, grupo: str) -> pd.DataFrame:
    """Comparaciones post-hoc de Games-Howell, robustas a varianzas desiguales.

    Es la alternativa correcta a Tukey HSD cuando Levene rechaza la
    homocedasticidad, que es lo que ocurre aquí.
    """
    d = df[[variable, grupo]].dropna()
    g = {k: v[variable].values for k, v in d.groupby(grupo, observed=True)}
    claves = list(g)
    filas = []
    for i, a in enumerate(claves):
        for b in claves[i + 1:]:
            xa, xb = g[a], g[b]
            na, nb = len(xa), len(xb)
            va, vb = xa.var(ddof=1), xb.var(ddof=1)
            dif = xb.mean() - xa.mean()
            se = np.sqrt(va / na + vb / nb)
            gl = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
            t = abs(dif) / se
            p = stats.studentized_range.sf(t * np.sqrt(2), len(claves), gl)
            q = stats.studentized_range.ppf(0.95, len(claves), gl) / np.sqrt(2)
            filas.append({
                "grupo_a": str(a), "grupo_b": str(b), "n_a": na, "n_b": nb,
                "media_a": xa.mean(), "media_b": xb.mean(), "diferencia": dif,
                "ic_inf": dif - q * se, "ic_sup": dif + q * se,
                "t": t, "gl": gl, "p": min(p, 1.0),
                "significativo": p < 0.05,
            })
    return pd.DataFrame(filas).sort_values("p")


# ─────────────────────────────────────────────────────────────────────
# Diagnósticos de regresión lineal
# ─────────────────────────────────────────────────────────────────────


def diagnostico_regresion(modelo, umbral_cook: float | None = None) -> dict:
    """Batería completa de diagnósticos sobre un modelo lineal ajustado.

    Cubre normalidad de residuos, homocedasticidad (Breusch-Pagan), influencia
    (distancia de Cook y leverage) y no linealidad (prueba RESET de Ramsey).
    """
    from statsmodels.stats.diagnostic import linear_reset

    n, k = int(modelo.nobs), int(modelo.df_model) + 1
    infl = modelo.get_influence()
    cook = infl.cooks_distance[0]
    leverage = infl.hat_matrix_diag
    umbral_cook = umbral_cook or 4 / n
    umbral_lev = 2 * k / n

    norm = normalidad(modelo.resid)
    bp = breusch_pagan(modelo)
    try:
        reset = linear_reset(modelo, power=2, use_f=True)
        p_reset, stat_reset = float(reset.pvalue), float(reset.statistic)
    except Exception:
        p_reset, stat_reset = np.nan, np.nan

    return {
        "n": n, "k_parametros": k,
        "r2": modelo.rsquared, "r2_ajustado": modelo.rsquared_adj,
        "normalidad_p": norm["p"], "asimetria_residuos": norm["asimetria"],
        "curtosis_residuos": norm["curtosis"], "normalidad_veredicto": norm["veredicto"],
        "breusch_pagan_p": bp["p"], "homocedasticidad_veredicto": bp["veredicto"],
        "reset_p": p_reset, "reset_estadistico": stat_reset,
        "linealidad_veredicto": ("Forma funcional adecuada" if p_reset >= 0.05
                                 else "RESET rechaza linealidad: considerar términos no lineales"),
        "n_influyentes_cook": int((cook > umbral_cook).sum()),
        "pct_influyentes_cook": float((cook > umbral_cook).mean() * 100),
        "cook_maximo": float(cook.max()),
        "n_leverage_alto": int((leverage > umbral_lev).sum()),
        "umbral_cook": umbral_cook, "umbral_leverage": umbral_lev,
    }


def sobredispersion(modelo_poisson) -> dict:
    """Evalúa sobredispersión en un modelo de Poisson.

    Si la razón entre el chi-cuadrado de Pearson y los grados de libertad supera
    claramente 1, la varianza excede a la media y procede una binomial negativa.
    """
    chi2 = float((modelo_poisson.resid_pearson ** 2).sum())
    gl = int(modelo_poisson.df_resid)
    razon = chi2 / gl
    return {
        "chi2_pearson": chi2, "gl": gl, "razon": razon,
        "hay_sobredispersion": razon > 1.5,
        "veredicto": ("Sin sobredispersión relevante: Poisson es adecuado" if razon <= 1.5
                      else f"Sobredispersión (razón = {razon:.2f}): usar binomial negativa"),
    }


def resumen_supuestos(diagnosticos: dict, nombre_modelo: str) -> pd.DataFrame:
    """Convierte un diccionario de diagnósticos en una tabla legible."""
    return pd.DataFrame([
        {"modelo": nombre_modelo, "supuesto": "Normalidad de residuos",
         "estadistico": f"asimetría {diagnosticos['asimetria_residuos']:.3f}, "
                        f"curtosis {diagnosticos['curtosis_residuos']:.3f}",
         "p": diagnosticos["normalidad_p"], "veredicto": diagnosticos["normalidad_veredicto"]},
        {"modelo": nombre_modelo, "supuesto": "Homocedasticidad",
         "estadistico": "Breusch-Pagan", "p": diagnosticos["breusch_pagan_p"],
         "veredicto": diagnosticos["homocedasticidad_veredicto"]},
        {"modelo": nombre_modelo, "supuesto": "Linealidad",
         "estadistico": f"RESET F = {diagnosticos['reset_estadistico']:.2f}",
         "p": diagnosticos["reset_p"], "veredicto": diagnosticos["linealidad_veredicto"]},
        {"modelo": nombre_modelo, "supuesto": "Observaciones influyentes",
         "estadistico": f"{diagnosticos['n_influyentes_cook']} casos con D de Cook > "
                        f"{diagnosticos['umbral_cook']:.5f} "
                        f"({diagnosticos['pct_influyentes_cook']:.1f} %)",
         "p": np.nan,
         "veredicto": ("Sin influencia desproporcionada"
                       if diagnosticos["pct_influyentes_cook"] < 5
                       else "Revisar casos influyentes")},
    ])
