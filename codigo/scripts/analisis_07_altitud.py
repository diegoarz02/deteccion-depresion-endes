"""Fase 2 · Altitud y depresión (§6 de la segunda corrida).

Línea de análisis nueva. `HV040` da la altitud del conglomerado y estaba sin
usar. Tiene sentido con lo que ya se encontró —Puno 12,8 % frente a Ucayali
1,1 %, altiplano contra selva baja— y hay literatura internacional sobre
hipoxia crónica de altura y trastornos del ánimo.

Existe además un precedente directo con la misma encuesta:

    Zegarra-Rodríguez CA, Plasencia-Dueñas NR, Failoc-Rojas VE (2022).
    Disparities in the prevalence of screened depression at different altitudes
    in Peru: A retrospective analysis of the ENDES 2019. PLOS ONE 17(12):
    e0278947. https://doi.org/10.1371/journal.pone.0278947

Ellos usaron cortes de 1 500 y 2 500 m sobre ENDES 2019 y encontraron razones
de prevalencia ajustadas de 1,38 y 1,41. Aquí se replican **sus cortes** además
de los pisos altitudinales peruanos, para que la comparación sea directa.

**Advertencia metodológica.** La altitud correlaciona con ruralidad, pobreza,
lengua materna y acceso a servicios. Nada de lo que sigue permite afirmar que
la altura *cause* depresión. Se reporta como hipótesis generadora.

Uso
---
    python codigo/scripts/analisis_07_altitud.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402
from depresion import encuesta as enc  # noqa: E402
from depresion import (
    geo,  # noqa: E402
    viz,  # noqa: E402
)
from depresion import io as dio  # noqa: E402
from depresion import modelos as mod  # noqa: E402
from depresion import supuestos as sup  # noqa: E402

COL = cfg.COLORES

#: Cortes de Zegarra-Rodríguez et al. (2022) sobre ENDES 2019, para comparar.
CORTES_PLOS = [(0, 1500, "< 1 500 m"), (1500, 2500, "1 500-2 499 m"),
               (2500, 10000, "≥ 2 500 m")]

AJUSTE = ["es_mujer", "grupo_etario", "educacion_grupo", "es_rural",
          "hta_dx", "diabetes_dx", "fuma_12m", "consumo_frecuente"]


def preparar(df: pd.DataFrame) -> pd.DataFrame:
    """Añade la categorización de altitud comparable con la literatura."""
    d = df[(df.en_analisis == 1)].dropna(subset=["depresion_bin", "altitud"]).copy()
    cats = pd.Series(pd.NA, index=d.index, dtype="object")
    for lo, hi, etq in CORTES_PLOS:
        cats[(d.altitud >= lo) & (d.altitud < hi)] = etq
    d["altitud_plos"] = pd.Categorical(cats, categories=[e for _, _, e in CORTES_PLOS],
                                       ordered=True)
    return d


# ─────────────────────────────────────────────────────────────────────
# 1. Descriptivo
# ─────────────────────────────────────────────────────────────────────


def descripcion(d: pd.DataFrame) -> pd.DataFrame:
    """Resume la distribución de altitud de la muestra."""
    a = d.altitud
    filas = [
        {"estadistico": "n", "valor": f"{len(a):,}"},
        {"estadistico": "Mínimo", "valor": f"{a.min():,.0f} m"},
        {"estadistico": "Percentil 25", "valor": f"{a.quantile(.25):,.0f} m"},
        {"estadistico": "Mediana", "valor": f"{a.median():,.0f} m"},
        {"estadistico": "Percentil 75", "valor": f"{a.quantile(.75):,.0f} m"},
        {"estadistico": "Máximo", "valor": f"{a.max():,.0f} m"},
        {"estadistico": "Media", "valor": f"{a.mean():,.0f} m"},
        {"estadistico": "% por encima de 2 500 m", "valor": f"{(a >= 2500).mean() * 100:.1f} %"},
        {"estadistico": "% por encima de 3 500 m", "valor": f"{(a >= 3500).mean() * 100:.1f} %"},
    ]
    return pd.DataFrame(filas)


def prevalencias(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Prevalencia ponderada por piso altitudinal y por los cortes de la literatura.

    Trabaja sobre una copia: convertir las categóricas a texto sobre el
    DataFrame original destruiría el orden de las categorías y, con él, la
    categoría de referencia de los modelos que vienen después.
    """
    d = d.copy()
    for col in ("altitud_categoria", "altitud_plos"):
        d[col] = d[col].astype(str)
    diseno = enc.crear_diseno(d, ["depresion_bin", "altitud_categoria", "altitud_plos"])

    pisos = enc.prevalencia(diseno, "depresion_bin", por="altitud_categoria")
    pisos = pisos.rename(columns={"est": "prevalencia", "lci": "ic_inf", "uci": "ic_sup"})
    pisos["n"] = pisos.altitud_categoria.map(d.altitud_categoria.value_counts())
    pisos = pisos.set_index("altitud_categoria").reindex(geo.ORDEN_PISOS).reset_index()

    plos = enc.prevalencia(diseno, "depresion_bin", por="altitud_plos")
    plos = plos.rename(columns={"est": "prevalencia", "lci": "ic_inf", "uci": "ic_sup"})
    plos["n"] = plos.altitud_plos.map(d.altitud_plos.value_counts())
    plos = plos.set_index("altitud_plos").reindex([e for _, _, e in CORTES_PLOS]).reset_index()
    plos["referencia_endes_2019"] = [5.48, 7.23, 7.12]
    return pisos, plos


# ─────────────────────────────────────────────────────────────────────
# 2. ANOVA
# ─────────────────────────────────────────────────────────────────────


def anova_altitud(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Contrasta el puntaje PHQ-9 entre pisos altitudinales."""
    r = sup.anova_completo(d, "phq9_score", "altitud_categoria")
    gh = sup.games_howell(d, "phq9_score", "altitud_categoria")
    return pd.DataFrame([r]), gh


# ─────────────────────────────────────────────────────────────────────
# 3. Modelos
# ─────────────────────────────────────────────────────────────────────


def modelos_altitud(d: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Ajusta la altitud en la logística, cruda y ajustada, con y sin no linealidad.

    Se prueba la forma funcional antes de dar por buena la lineal: el efecto de
    la altura podría concentrarse en un tramo y no crecer de forma constante.
    """
    filas = {}

    # (a) Cruda, continua, por cada 100 m
    r_cruda = mod.logistica(d, "depresion_bin", ["altitud_100m"], con_diseno=True)
    filas["cruda"] = r_cruda["tabla_or"].iloc[0]

    # (b) Ajustada por los confusores del DAG
    r_aj = mod.logistica(d, "depresion_bin", ["altitud_100m", *AJUSTE], con_diseno=True,
                         referencias={"grupo_etario": "30-39", "educacion_grupo": "Superior"})
    filas["ajustada"] = r_aj["tabla_or"].set_index("termino").loc["altitud_100m"]

    # (c) Ajustada + región natural: ¿queda algo tras controlar por la geografía?
    r_reg = mod.logistica(d, "depresion_bin", ["altitud_100m", *AJUSTE, "region_natural"],
                          con_diseno=True,
                          referencias={"grupo_etario": "30-39", "educacion_grupo": "Superior",
                                       "region_natural": "Costa"})
    filas["ajustada_mas_region"] = r_reg["tabla_or"].set_index("termino").loc["altitud_100m"]

    # (d) Categórica por pisos, que no impone forma funcional alguna
    r_cat = mod.logistica(d, "depresion_bin", ["altitud_categoria", *AJUSTE], con_diseno=True,
                          referencias={"altitud_categoria": geo.ORDEN_PISOS[0],
                                       "grupo_etario": "30-39", "educacion_grupo": "Superior"})

    tabla = pd.DataFrame([
        {"modelo": "(a) Cruda", "termino": "Altitud (por 100 m)",
         "or": filas["cruda"]["or"], "ic_inf": filas["cruda"].ic_inf,
         "ic_sup": filas["cruda"].ic_sup, "p": filas["cruda"].p,
         "ajuste": "ninguno"},
        {"modelo": "(b) Ajustada", "termino": "Altitud (por 100 m)",
         "or": filas["ajustada"]["or"], "ic_inf": filas["ajustada"].ic_inf,
         "ic_sup": filas["ajustada"].ic_sup, "p": filas["ajustada"].p,
         "ajuste": "sexo, edad, educación, área, crónicas, tabaco, alcohol"},
        {"modelo": "(c) Ajustada + región", "termino": "Altitud (por 100 m)",
         "or": filas["ajustada_mas_region"]["or"], "ic_inf": filas["ajustada_mas_region"].ic_inf,
         "ic_sup": filas["ajustada_mas_region"].ic_sup, "p": filas["ajustada_mas_region"].p,
         "ajuste": "lo anterior + región natural"},
    ])
    tabla["or_formato"] = tabla.apply(
        lambda r: f"{r['or']:.3f} ({r.ic_inf:.3f} – {r.ic_sup:.3f})", axis=1)
    tabla["por_1000m"] = tabla["or"] ** 10  # efecto acumulado de mil metros

    return tabla, {"categorica": r_cat["tabla_or"], "ajustada": r_aj}


def evaluar_no_linealidad(d: pd.DataFrame) -> pd.DataFrame:
    """Compara forma lineal, cuadrática y con splines para la altitud.

    Si el efecto se concentra en un tramo —por ejemplo, solo por encima de los
    2 500 m—, el modelo lineal lo diluiría y podría declararlo nulo.
    """
    dd = d.dropna(subset=["depresion_bin", "altitud_100m"]).copy()
    y = dd.depresion_bin.astype(float)
    filas = []

    def ajustar(nombre, X, descripcion):
        m = sm.GLM(y, sm.add_constant(X), family=sm.families.Binomial()).fit()
        filas.append({"forma": nombre, "descripcion": descripcion, "aic": m.aic,
                      "gl": int(m.df_model), "log_verosimilitud": m.llf})
        return m

    m_lin = ajustar("Lineal", dd[["altitud_100m"]], "Altitud como continua")
    X2 = dd[["altitud_100m"]].copy()
    X2["altitud_cuad"] = X2.altitud_100m ** 2
    m_cua = ajustar("Cuadrática", X2, "Se permite curvatura")

    # Spline natural con nudos en los cuantiles: la forma la deciden los datos.
    nudos = np.quantile(dd.altitud_100m, [0.25, 0.5, 0.75])
    Xs = dd[["altitud_100m"]].copy()
    for i, k in enumerate(nudos):
        Xs[f"spline_{i}"] = np.maximum(dd.altitud_100m - k, 0) ** 3
    ajustar("Spline cúbico", Xs, f"Nudos en {[round(k * 100) for k in nudos]} m")

    out = pd.DataFrame(filas)
    out["delta_aic"] = out.aic - out.aic.min()
    mejor = out.loc[out.aic.idxmin(), "forma"]
    out["veredicto"] = np.where(
        out.forma == mejor, "Mejor ajuste por AIC",
        "Peor que el mejor por " + out.delta_aic.round(1).astype(str) + " puntos de AIC")

    # Prueba formal de la curvatura
    lr = 2 * (m_cua.llf - m_lin.llf)
    from scipy import stats as st
    out.attrs["p_curvatura"] = float(st.chi2.sf(lr, 1))
    out.attrs["mejor"] = mejor
    return out


def razon_prevalencias_por_categoria(d: pd.DataFrame) -> pd.DataFrame:
    """Razón de prevalencias ajustada por categoría, comparable con el PLOS ONE.

    Ellos reportaron aPR, no OR, así que para comparar hay que estimar lo mismo:
    Poisson con varianza robusta.
    """
    dd = d.dropna(subset=["depresion_bin", "altitud_plos", *AJUSTE]).copy()

    # La referencia se fija a mano en el tramo bajo. Dejarla al azar de
    # `drop_first` haría que el estimador dejase de ser comparable con el
    # estudio de ENDES 2019, que usa "< 1 500 m" como categoría base.
    referencia = CORTES_PLOS[0][2]
    for _, _, etq in CORTES_PLOS[1:]:
        dd[f"alt__{etq}"] = (dd.altitud_plos.astype(str) == etq).astype(float)
    columnas_alt = [f"alt__{e}" for _, _, e in CORTES_PLOS[1:]]

    X = pd.concat([dd[columnas_alt],
                   pd.get_dummies(dd[AJUSTE], drop_first=True).astype(float)], axis=1)
    m = sm.GLM(dd.depresion_bin.astype(float), sm.add_constant(X),
               family=sm.families.Poisson()).fit(cov_type="HC0")

    equivalencias = {"1 500-2 499 m": "1,38 (1,04 – 1,84)", "≥ 2 500 m": "1,41 (1,20 – 1,66)"}
    filas = []
    for t in columnas_alt:
        etq = t.replace("alt__", "")
        b, se = m.params[t], m.bse[t]
        filas.append({
            "categoria": etq, "referencia": referencia,
            "n": int((dd.altitud_plos.astype(str) == etq).sum()),
            "rp_ajustada": np.exp(b),
            "ic_inf": np.exp(b - 1.96 * se), "ic_sup": np.exp(b + 1.96 * se),
            "p": m.pvalues[t],
            "referencia_endes_2019": equivalencias.get(etq, ""),
        })
    out = pd.DataFrame(filas)
    out["rp_formato"] = out.apply(
        lambda r: f"{r.rp_ajustada:.2f} ({r.ic_inf:.2f} – {r.ic_sup:.2f})", axis=1)
    return out


# ─────────────────────────────────────────────────────────────────────
# 4. Figuras
# ─────────────────────────────────────────────────────────────────────


def figura_altitud(pisos: pd.DataFrame, d: pd.DataFrame, no_lin: pd.DataFrame) -> None:
    """Panel de tres: distribución, prevalencia por piso y curva suavizada."""
    viz.aplicar_tema()
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(16, 5.2))

    a1.hist(d.altitud, bins=60, color=COL["navy"], alpha=0.9)
    for corte, etq in [(1500, "1 500 m"), (2500, "2 500 m")]:
        a1.axvline(corte, color=COL["ambar"], linestyle="--", linewidth=1.4)
        a1.text(corte + 60, a1.get_ylim()[1] * 0.9, etq, fontsize=8.5, color=COL["ambar"])
    a1.set_xlabel("Altitud del conglomerado (m)")
    a1.set_ylabel("Personas")
    a1.set_title("Dónde vive la muestra")

    y = np.arange(len(pisos))
    a2.barh(y, pisos.prevalencia, color=COL["navy"], height=0.68)
    a2.errorbar(pisos.prevalencia, y,
                xerr=[pisos.prevalencia - pisos.ic_inf, pisos.ic_sup - pisos.prevalencia],
                fmt="none", ecolor=COL["dorado"], elinewidth=1.6, capsize=3)
    a2.set_yticks(y)
    a2.set_yticklabels([e.split(" (")[0] for e in pisos.altitud_categoria], fontsize=9)
    a2.set_xlabel("Prevalencia ponderada (%)")
    a2.set_title("Prevalencia por piso altitudinal")

    # Prevalencia observada en tramos de 250 m, con su tamaño de muestra
    d2 = d.copy()
    d2["tramo"] = (d2.altitud // 250) * 250
    g = d2.groupby("tramo").agg(prev=("depresion_bin", "mean"), n=("depresion_bin", "size"))
    g = g[g.n >= 100]
    a3.scatter(g.index, g.prev * 100, s=np.sqrt(g.n) * 2.2, color=COL["navy"], alpha=0.65)
    z = np.polyfit(g.index, g.prev * 100, 2)
    xs = np.linspace(g.index.min(), g.index.max(), 200)
    a3.plot(xs, np.polyval(z, xs), color=COL["rojo"], linewidth=2)
    a3.set_xlabel("Altitud (m)")
    a3.set_ylabel("Prevalencia cruda (%)")
    a3.set_title("Tendencia por tramos de 250 m")
    a3.text(0.03, 0.95, f"Mejor forma por AIC:\n{no_lin.attrs['mejor']}",
            transform=a3.transAxes, va="top", fontsize=8.5, color=COL["gris"],
            bbox={"boxstyle": "round,pad=0.4", "facecolor": "#F7F9FC",
                  "edgecolor": COL["gris_claro"]})

    fig.suptitle("Altitud y sintomatología depresiva", fontsize=14, fontweight="bold",
                 color=COL["navy"], y=1.02)
    fig.tight_layout()
    viz.pie_de_figura(
        fig, "Fuente: ENDES 2025 (INEI). El tamaño del punto es proporcional al número de "
             "personas del tramo. La altitud correlaciona con ruralidad y pobreza: no es causal.")
    dio.guardar_figura(fig, "fig_15_altitud")
    plt.close(fig)


def figura_dispersion_departamental(d: pd.DataFrame) -> pd.DataFrame:
    """Prevalencia departamental frente a altitud media, con línea de tendencia."""
    viz.aplicar_tema()
    g = d.groupby("departamento").apply(
        lambda x: pd.Series({
            "altitud_media": x.altitud.mean(),
            "prevalencia": np.average(x.depresion_bin, weights=x.peso) * 100,
            "n": len(x)}),
        include_groups=False).reset_index()

    r, p = __import__("scipy.stats", fromlist=["pearsonr"]).pearsonr(
        g.altitud_media, g.prevalencia)
    rho, p_rho = __import__("scipy.stats", fromlist=["spearmanr"]).spearmanr(
        g.altitud_media, g.prevalencia)

    fig, ax = plt.subplots(figsize=(10.5, 6.6))
    ax.scatter(g.altitud_media, g.prevalencia, s=70, color=COL["navy"], alpha=0.8, zorder=3)
    z = np.polyfit(g.altitud_media, g.prevalencia, 1)
    xs = np.linspace(g.altitud_media.min(), g.altitud_media.max(), 100)
    ax.plot(xs, np.polyval(z, xs), color=COL["rojo"], linewidth=2, zorder=2)
    for _, r_ in g.iterrows():
        ax.annotate(r_.departamento, (r_.altitud_media, r_.prevalencia),
                    fontsize=7.5, color=COL["gris"], xytext=(4, 4),
                    textcoords="offset points")
    ax.set_xlabel("Altitud media del departamento (m)")
    ax.set_ylabel("Prevalencia ponderada de depresión (%)")
    ax.set_title("Los departamentos más altos concentran más sintomatología depresiva")
    ax.text(0.03, 0.95,
            f"Pearson r = {r:.3f} (p = {p:.4f})\nSpearman ρ = {rho:.3f} (p = {p_rho:.4f})\n"
            f"25 departamentos",
            transform=ax.transAxes, va="top", fontsize=10, color=COL["navy"],
            bbox={"boxstyle": "round,pad=0.5", "facecolor": "#F7F9FC",
                  "edgecolor": COL["gris_claro"]})
    viz.pie_de_figura(
        fig, "Fuente: ENDES 2025 (INEI). Correlación ecológica entre agregados "
             "departamentales: no permite inferir sobre individuos.")
    dio.guardar_figura(fig, "fig_16_altitud_departamento")
    plt.close(fig)
    g.attrs["pearson"] = (r, p)
    g.attrs["spearman"] = (rho, p_rho)
    return g


def main() -> None:
    """Ejecuta el análisis completo de altitud."""
    dio.configurar_logging()
    df = pd.read_parquet(cfg.DATASET_FINAL)
    d = preparar(df)
    print(f"Población de análisis con altitud: {len(d):,}\n")

    desc = descripcion(d)
    dio.guardar_tabla(desc, "tabla_32_descripcion_altitud",
                      "Distribución de la altitud en la muestra")
    print(desc.to_string(index=False))

    pisos, plos = prevalencias(d)
    dio.guardar_tabla(pisos, "tabla_33_prevalencia_por_altitud",
                      "Prevalencia ponderada de depresión por piso altitudinal")
    dio.guardar_tabla(plos, "tabla_34_altitud_cortes_literatura",
                      "Prevalencia por los cortes de Zegarra-Rodríguez et al. (2022)")
    print("\n" + "=" * 96)
    print("PREVALENCIA POR PISO ALTITUDINAL")
    print("=" * 96)
    print(pisos[["altitud_categoria", "n", "prevalencia", "lci" if "lci" in pisos else "ic_inf",
                 "ic_sup"]].to_string(index=False))
    print("\nComparación con ENDES 2019 (PLOS ONE 2022):")
    print(plos[["altitud_plos", "n", "prevalencia", "ic_inf", "ic_sup",
                "referencia_endes_2019"]].to_string(index=False))

    anovas, gh = anova_altitud(d)
    dio.guardar_tabla(anovas, "tabla_35_anova_altitud", "ANOVA del PHQ-9 por piso altitudinal")
    dio.guardar_tabla(gh, "tabla_36_posthoc_altitud", "Post-hoc de Games-Howell por altitud")
    r = anovas.iloc[0]
    print(f"\nANOVA: {r.veredicto}")
    print(f"  Kruskal-Wallis H = {r.H_kruskal:.2f}, p = {r.p_kruskal:.2e}, η² = {r.eta2:.4f}")

    no_lin = evaluar_no_linealidad(d)
    dio.guardar_tabla(no_lin, "tabla_37_forma_funcional_altitud",
                      "Comparación de formas funcionales para la altitud")
    print("\n" + "=" * 96)
    print("FORMA FUNCIONAL")
    print("=" * 96)
    print(no_lin[["forma", "descripcion", "aic", "delta_aic", "veredicto"]].to_string(index=False))
    print(f"  Prueba de curvatura (lineal vs cuadrática): p = {no_lin.attrs['p_curvatura']:.4f}")

    tabla_mod, extras = modelos_altitud(d)
    dio.guardar_tabla(tabla_mod, "tabla_38_altitud_modelos",
                      "OR de la altitud, crudo y ajustado")
    dio.guardar_tabla(extras["categorica"], "tabla_39_altitud_categorica",
                      "OR ajustado por piso altitudinal")
    print("\n" + "=" * 96)
    print("¿SOBREVIVE LA ALTITUD AL AJUSTE?")
    print("=" * 96)
    print(tabla_mod[["modelo", "or_formato", "p", "por_1000m", "ajuste"]].to_string(index=False))

    rp = razon_prevalencias_por_categoria(d)
    dio.guardar_tabla(rp, "tabla_40_altitud_rp_ajustada",
                      "Razón de prevalencias ajustada por altitud, comparable con ENDES 2019")
    print("\nRazón de prevalencias ajustada (comparable con el estudio de ENDES 2019):")
    print(rp[["categoria", "referencia", "n", "rp_formato", "p", "referencia_endes_2019"]].to_string(index=False))

    figura_altitud(pisos, d, no_lin)
    g = figura_dispersion_departamental(d)
    dio.guardar_tabla(g, "tabla_41_altitud_departamento",
                      "Altitud media y prevalencia por departamento")
    print(f"\nCorrelación ecológica departamental: Pearson r = {g.attrs['pearson'][0]:.3f} "
          f"(p = {g.attrs['pearson'][1]:.4f})")
    print("\nAnálisis de altitud completado.")


if __name__ == "__main__":
    main()
