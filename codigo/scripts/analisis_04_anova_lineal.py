"""Fase 2 · ANOVA de un factor y regresión lineal múltiple (§11.3 del protocolo).

El PHQ-9 tiene asimetría 2,4 y la mitad de la muestra en cero, así que la
regresión lineal cruda viola normalidad y homocedasticidad. La política aquí es
**declarar el problema y comparar cuatro tratamientos**, no esconderlo:

    (a) modelo crudo
    (b) transformación raíz cuadrada
    (c) errores estándar robustos HC3
    (d) alternativa de conteo (Poisson y binomial negativa)

Uso
---
    python codigo/scripts/analisis_04_anova_lineal.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402
from depresion import io as dio  # noqa: E402
from depresion import supuestos as sup  # noqa: E402
from depresion import viz  # noqa: E402

# Ojo: no llamar a esta constante "C": patsy usa C() para declarar
# categóricas en las fórmulas, y el nombre quedaría tapado.
COL = cfg.COLORES

FACTORES = [("grupo_etario", "Grupo etario"),
            ("educacion_grupo", "Nivel educativo"),
            ("region_natural", "Región natural")]

PREDICTORES = ["es_mujer", "edad", "educacion_grupo", "es_rural", "region_natural",
               "consumo_frecuente", "alcohol_problematico", "fuma_12m",
               "hta_dx", "diabetes_dx", "obesidad"]


# ─────────────────────────────────────────────────────────────────────
# ANOVA
# ─────────────────────────────────────────────────────────────────────


def ejecutar_anovas(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ejecuta el ANOVA de un factor para cada factor, con post-hoc."""
    resultados, posthoc = [], []
    for f, etq in FACTORES:
        r = sup.anova_completo(df, "phq9_score", f)
        r["factor_etiqueta"] = etq
        resultados.append(r)
        gh = sup.games_howell(df, "phq9_score", f)
        gh.insert(0, "factor", etq)
        posthoc.append(gh)
    return pd.DataFrame(resultados), pd.concat(posthoc, ignore_index=True)


def figura_anova(df: pd.DataFrame, anovas: pd.DataFrame) -> None:
    """Diagramas de caja del PHQ-9 por cada factor, con la media marcada."""
    viz.aplicar_tema()
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.4))
    for ax, (f, etq) in zip(axes, FACTORES, strict=False):
        d = df[[f, "phq9_score"]].dropna()
        cats = list(d[f].astype(str).unique())
        cats.sort(key=lambda c: d.loc[d[f].astype(str) == c, "phq9_score"].mean())
        datos = [d.loc[d[f].astype(str) == c, "phq9_score"].values for c in cats]
        bp = ax.boxplot(datos, patch_artist=True, showfliers=False, widths=0.62,
                        medianprops={"color": COL["rojo"], "linewidth": 1.8})
        for caja, col in zip(bp["boxes"], cfg.PALETA_SECUENCIAL[1:], strict=False):
            caja.set_facecolor(col)
            caja.set_alpha(0.85)
        medias = [x.mean() for x in datos]
        ax.plot(range(1, len(cats) + 1), medias, "o", color=COL["dorado"],
                markersize=7, label="Media", zorder=5)
        ax.set_xticks(range(1, len(cats) + 1))
        ax.set_xticklabels(cats, rotation=30, ha="right", fontsize=9)
        ax.set_title(etq, fontsize=12)
        r = anovas[anovas.factor == f].iloc[0]
        ax.text(0.03, 0.96, f"η² = {r.eta2:.4f}\n({r.magnitud_efecto})\n{r.prueba_valida}",
                transform=ax.transAxes, va="top", fontsize=8.5, color=COL["gris"],
                bbox={"boxstyle": "round,pad=0.45", "facecolor": "#F7F9FC",
                      "edgecolor": COL["gris_claro"]})
        if ax is axes[0]:
            ax.set_ylabel("Puntaje PHQ-9")
            ax.legend(loc="upper right", fontsize=9)
    fig.suptitle("Puntaje PHQ-9 por factor — ANOVA de un factor", fontsize=14,
                 fontweight="bold", color=COL["navy"], y=1.02)
    viz.pie_de_figura(fig)
    dio.guardar_figura(fig, "fig_09_anova_boxplots")
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────
# Regresión lineal
# ─────────────────────────────────────────────────────────────────────


def formula(y: str) -> str:
    """Construye la fórmula del modelo con los factores como categóricas."""
    términos = []
    for v in PREDICTORES:
        términos.append(f"C({v})" if v in ("educacion_grupo", "region_natural") else v)
    return f"{y} ~ " + " + ".join(términos)


def ejecutar_regresiones(df: pd.DataFrame) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    """Ajusta las cuatro versiones del modelo lineal y compara sus supuestos."""
    d = df.dropna(subset=["phq9_score", *PREDICTORES]).copy()
    d["phq9_raiz"] = np.sqrt(d.phq9_score)
    d["phq9_log"] = np.log1p(d.phq9_score)

    modelos, diagnosticos, comparacion = {}, [], []

    # (a) crudo
    m_crudo = smf.ols(formula("phq9_score"), data=d).fit()
    modelos["crudo"] = m_crudo
    dg = sup.diagnostico_regresion(m_crudo)
    diagnosticos.append(sup.resumen_supuestos(dg, "(a) Lineal crudo"))
    comparacion.append({"modelo": "(a) Lineal crudo", "n": int(m_crudo.nobs),
                        "r2": m_crudo.rsquared, "aic": m_crudo.aic,
                        "asimetria_resid": dg["asimetria_residuos"],
                        "bp_p": dg["breusch_pagan_p"]})

    # (b) transformación raíz cuadrada
    m_raiz = smf.ols(formula("phq9_raiz"), data=d).fit()
    modelos["raiz"] = m_raiz
    dg_r = sup.diagnostico_regresion(m_raiz)
    diagnosticos.append(sup.resumen_supuestos(dg_r, "(b) Raíz cuadrada"))
    comparacion.append({"modelo": "(b) Raíz cuadrada", "n": int(m_raiz.nobs),
                        "r2": m_raiz.rsquared, "aic": m_raiz.aic,
                        "asimetria_resid": dg_r["asimetria_residuos"],
                        "bp_p": dg_r["breusch_pagan_p"]})

    # (c) errores robustos HC3 sobre el modelo crudo
    m_hc3 = smf.ols(formula("phq9_score"), data=d).fit(cov_type="HC3")
    modelos["hc3"] = m_hc3
    comparacion.append({"modelo": "(c) Crudo con HC3", "n": int(m_hc3.nobs),
                        "r2": m_hc3.rsquared, "aic": np.nan,
                        "asimetria_resid": dg["asimetria_residuos"], "bp_p": np.nan})

    # (d) alternativas de conteo
    m_pois = smf.glm(formula("phq9_score"), data=d, family=sm.families.Poisson()).fit()
    sd = sup.sobredispersion(m_pois)
    modelos["poisson"] = m_pois
    comparacion.append({"modelo": "(d1) Poisson", "n": int(m_pois.nobs), "r2": np.nan,
                        "aic": m_pois.aic, "asimetria_resid": np.nan, "bp_p": np.nan})

    alfa = max(sd["razon"] - 1, 0.1)
    m_nb = smf.glm(formula("phq9_score"), data=d,
                   family=sm.families.NegativeBinomial(alpha=alfa)).fit()
    modelos["binomial_negativa"] = m_nb
    comparacion.append({"modelo": f"(d2) Binomial negativa (α={alfa:.2f})",
                        "n": int(m_nb.nobs), "r2": np.nan, "aic": m_nb.aic,
                        "asimetria_resid": np.nan, "bp_p": np.nan})

    diag = pd.concat(diagnosticos, ignore_index=True)
    diag.loc[len(diag)] = {"modelo": "(d1) Poisson", "supuesto": "Sobredispersión",
                           "estadistico": f"χ²/gl = {sd['razon']:.3f}", "p": np.nan,
                           "veredicto": sd["veredicto"]}

    comp = pd.DataFrame(comparacion)
    # El AIC solo compara modelos sobre la MISMA variable respuesta. Los modelos
    # (a), (c) y (d) modelan phq9_score; el (b) modela su raíz cuadrada, y su AIC
    # no es comparable con los demás por el jacobiano de la transformación.
    comp["escala_respuesta"] = ["PHQ-9", "raíz(PHQ-9)", "PHQ-9", "PHQ-9", "PHQ-9"]
    comp["aic_comparable"] = comp.escala_respuesta.eq("PHQ-9").map(
        {True: "sí, entre modelos de escala PHQ-9", False: "NO — otra escala de respuesta"})
    return modelos, comp, diag


def tabla_coeficientes(modelos: dict) -> pd.DataFrame:
    """Compara los coeficientes de las cuatro versiones lado a lado."""
    filas = []
    etiquetas = {"crudo": "(a) Crudo", "raiz": "(b) Raíz", "hc3": "(c) HC3",
                 "poisson": "(d1) Poisson", "binomial_negativa": "(d2) Bin. negativa"}
    for clave, m in modelos.items():
        for termino in m.params.index:
            if termino == "Intercept":
                continue
            filas.append({
                "modelo": etiquetas[clave], "termino": termino,
                "coeficiente": m.params[termino], "ee": m.bse[termino],
                "ic_inf": m.conf_int().loc[termino, 0], "ic_sup": m.conf_int().loc[termino, 1],
                "p": m.pvalues[termino],
            })
    return pd.DataFrame(filas)


def figura_diagnosticos(modelos: dict) -> None:
    """Panel de diagnóstico: Q-Q, residuos y comparación de transformaciones."""
    viz.aplicar_tema()
    fig, axes = plt.subplots(2, 3, figsize=(15.5, 9))

    for j, (clave, titulo) in enumerate([("crudo", "(a) PHQ-9 crudo"),
                                         ("raiz", "(b) Raíz cuadrada")]):
        m = modelos[clave]
        t, o = sup.qq_datos(m.resid)
        axes[j, 0].scatter(t, o, s=3, color=COL["navy"], alpha=0.28)
        lim = [min(t.min(), o.min()), max(t.max(), o.max())]
        axes[j, 0].plot(lim, lim, color=COL["rojo"], linewidth=1.4)
        axes[j, 0].set_title(f"Q-Q de residuos · {titulo}", fontsize=11)
        axes[j, 0].set_xlabel("Cuantiles teóricos")
        axes[j, 0].set_ylabel("Cuantiles observados")

        axes[j, 1].scatter(m.fittedvalues, m.resid, s=3, color=COL["navy"], alpha=0.22)
        axes[j, 1].axhline(0, color=COL["rojo"], linewidth=1.3)
        axes[j, 1].set_title(f"Residuos frente a ajustados · {titulo}", fontsize=11)
        axes[j, 1].set_xlabel("Valores ajustados")
        axes[j, 1].set_ylabel("Residuos")

        axes[j, 2].hist(m.resid, bins=60, color=COL["navy"], alpha=0.85)
        axes[j, 2].set_title(f"Distribución de residuos · {titulo}", fontsize=11)
        axes[j, 2].set_xlabel("Residuo")
        from scipy import stats as st
        axes[j, 2].text(0.97, 0.94,
                        f"asimetría {st.skew(m.resid):.2f}\ncurtosis {st.kurtosis(m.resid):.2f}",
                        transform=axes[j, 2].transAxes, ha="right", va="top",
                        fontsize=9, color=COL["gris"])
    fig.suptitle("Diagnóstico de supuestos de la regresión lineal", fontsize=14,
                 fontweight="bold", color=COL["navy"], y=1.0)
    fig.tight_layout()
    viz.pie_de_figura(
        fig, "Fuente: ENDES 2025 (INEI). La transformación mejora la simetría pero no "
             "elimina el exceso de ceros: la conclusión sustantiva se apoya en la logística.")
    dio.guardar_figura(fig, "fig_10_diagnostico_regresion")
    plt.close(fig)


def main() -> None:
    """Ejecuta el ANOVA y las cuatro versiones de la regresión lineal."""
    dio.configurar_logging()
    df = pd.read_parquet(cfg.DATASET_FINAL)
    base = df[df.en_analisis == 1].dropna(subset=["phq9_score"]).copy()
    print(f"Población de análisis: {len(base):,}\n")

    anovas, posthoc = ejecutar_anovas(base)
    dio.guardar_tabla(anovas, "tabla_16_anova", "ANOVA de un factor del puntaje PHQ-9")
    dio.guardar_tabla(posthoc, "tabla_17_posthoc_games_howell",
                      "Comparaciones post-hoc de Games-Howell")

    print("=" * 108)
    print("ANOVA DE UN FACTOR — PHQ-9")
    print("=" * 108)
    print(anovas[["factor_etiqueta", "n", "k_grupos", "F", "p_anova", "F_welch", "p_welch",
                  "H_kruskal", "p_kruskal", "eta2", "omega2", "levene_cumple",
                  "normalidad_cumple", "prueba_valida", "magnitud_efecto"]].to_string(index=False))
    for _, r in anovas.iterrows():
        print(f"\n  {r.factor_etiqueta}: {r.veredicto}")

    print("\nPost-hoc: comparaciones no significativas (las interesantes)")
    ns = posthoc[~posthoc.significativo]
    print(ns[["factor", "grupo_a", "grupo_b", "diferencia", "p"]].to_string(index=False)
          if len(ns) else "  Todas las comparaciones resultaron significativas.")

    modelos, comparacion, diag = ejecutar_regresiones(base)
    dio.guardar_tabla(comparacion, "tabla_18_comparacion_modelos_lineales",
                      "Comparación de las cuatro versiones del modelo lineal")
    dio.guardar_tabla(diag, "tabla_19_supuestos_regresion",
                      "Verificación de supuestos de la regresión lineal")
    dio.guardar_tabla(tabla_coeficientes(modelos), "tabla_20_coeficientes_lineales",
                      "Coeficientes de las cuatro versiones del modelo lineal")

    print("\n" + "=" * 108)
    print("REGRESIÓN LINEAL — CUATRO TRATAMIENTOS DEL SESGO")
    print("=" * 108)
    print(comparacion.to_string(index=False))
    print("\n" + "=" * 108)
    print("SUPUESTOS")
    print("=" * 108)
    with pd.option_context("display.max_colwidth", 82):
        print(diag.to_string(index=False))

    figura_anova(base, anovas)
    figura_diagnosticos(modelos)
    print("\nANOVA y regresión lineal completados.")


if __name__ == "__main__":
    main()
