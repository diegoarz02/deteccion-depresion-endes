"""Fase 2 · Medidas de asociación y riesgo atribuible basado en prevalencia.

Presenta la tabla 2×2 de cada factor principal con su OR, su razón de prevalencias, la prueba chi cuadrado y las
medidas de impacto que se pueden calcular en un corte transversal.

Qué calcula
-----------
1. Para cada exposición, la tabla 2×2 en notación a, b, c, d, con OR y RP crudos
   (IC 95 %), diferencia de prevalencias y chi cuadrado de Pearson, junto con la
   versión de Rao y Scott, que sí reconoce el muestreo por conglomerados.
2. Las medidas de impacto basadas en prevalencia, con pesos de la encuesta:
   diferencia de prevalencias, fracción atribuible en expuestos y fracción
   atribuible poblacional, crudas y ajustadas. La versión ajustada parte de la
   razón de prevalencias del mismo conjunto de covariables del modelo logístico
   principal (Poisson con enlace log y varianza de diseño); no es un modelo
   nuevo, es la misma especificación con otra medida.
3. Intervalos del 95 % por bootstrap de Rao y Wu (conglomerados dentro de
   estratos) para las fracciones, que son funciones no lineales de varias
   estimaciones.

Nada de esto cambia los coeficientes que sirve la API: son presentaciones
distintas de los mismos datos.

Uso
---
    python codigo/scripts/analisis_12_asociacion_atribuible.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from matplotlib.ticker import NullFormatter, NullLocator

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import atribuible as atr  # noqa: E402
from depresion import config as cfg  # noqa: E402
from depresion import encuesta as enc  # noqa: E402
from depresion import io as dio  # noqa: E402
from depresion import modelos as mod  # noqa: E402
from depresion import viz  # noqa: E402

warnings.filterwarnings("ignore")
COL = cfg.COLORES

#: Réplicas bootstrap. Con 1 000 el error de Monte Carlo de un límite de
#: percentil queda por debajo de una décima de punto porcentual.
N_REPLICAS = 1000

EXPOSICIONES = [
    ("violencia_fisica", "Violencia física de pareja"),
    ("es_mujer", "Sexo femenino"),
    ("hta_dx", "Hipertensión diagnosticada"),
    ("diabetes_dx", "Diabetes diagnosticada"),
    ("alcohol_problematico", "Consumo problemático de alcohol"),
    ("es_rural", "Área rural"),
    ("obesidad", "Obesidad (IMC ≥ 30)"),
    ("consumo_frecuente", "Consumo frecuente de alcohol"),
    ("fuma_12m", "Fumó en los últimos 12 meses"),
]
ETIQUETA = dict(EXPOSICIONES)

# Mismo conjunto de covariables que el modelo logístico principal
# (analisis_05_logistica.py); se repite aquí para que este script no dependa de
# importar otro script.
SOCIODEMOGRAFICAS = ["es_mujer", "grupo_etario", "educacion_grupo", "es_rural", "region_natural"]
CONDUCTUALES_CLINICAS = ["consumo_frecuente", "alcohol_problematico", "fuma_12m",
                         "hta_dx", "diabetes_dx", "obesidad"]
COMPLETO = SOCIODEMOGRAFICAS + CONDUCTUALES_CLINICAS
REFERENCIAS = {"grupo_etario": "30-39", "educacion_grupo": "Superior", "region_natural": "Costa"}


# ─────────────────────────────────────────────────────────────────────
# 1. Tablas 2×2
# ─────────────────────────────────────────────────────────────────────


def rao_scott(df: pd.DataFrame, exposicion: str) -> tuple[float, float]:
    """Prueba F de Rao y Scott de independencia exposición-desenlace.

    Corrige el chi cuadrado de Pearson por el efecto de diseño. Devuelve el
    estadístico F y su valor p.
    """
    d = df.dropna(subset=[exposicion, "depresion_bin"])
    s = enc.crear_diseno(d, [exposicion, "depresion_bin"])
    t = s.categorical.tabulate(rowvar=exposicion, colvar="depresion_bin", drop_nulls=True)
    return float(t.stats.f.value), float(t.stats.f.p_value)


def tabla_2x2_completa(base: pd.DataFrame) -> pd.DataFrame:
    """Una fila por exposición con celdas a, b, c, d y todas las medidas."""
    filas = []
    for v, etq in EXPOSICIONES:
        c = atr.celdas_abcd(base[v], base.depresion_bin)
        m = atr.medidas_2x2(**c)
        f_rs, p_rs = rao_scott(base, v)
        filas.append({
            "exposicion": etq, "variable": v, **c,
            "n_expuestos": m["n_expuestos"], "n_no_expuestos": m["n_no_expuestos"],
            "n": m["n"],
            "prev_expuestos": m["prev_expuestos"], "prev_no_expuestos": m["prev_no_expuestos"],
            "rd": m["rd"], "rd_ic_inf": m["rd_ic_inf"], "rd_ic_sup": m["rd_ic_sup"],
            "rp": m["rp"], "rp_ic_inf": m["rp_ic_inf"], "rp_ic_sup": m["rp_ic_sup"],
            "or": m["or"], "or_ic_inf": m["or_ic_inf"], "or_ic_sup": m["or_ic_sup"],
            "chi2": m["chi2"], "gl": 1, "p_chi2": m["p_chi2"],
            "esperada_minima": m["esperada_minima"],
            "f_rao_scott": f_rs, "p_rao_scott": p_rs,
            "lectura_sin_ponderar": atr.fuerza(m["rp"], m["rp_ic_inf"], m["rp_ic_sup"]),
            # La lectura definitiva exige que la asociación sobreviva al diseño: la tabla
            # cuenta personas sin ponderar y trata a todas como independientes, así que
            # puede mostrar una señal (incluso de signo contrario) que el diseño no sostiene.
            "lectura": (atr.fuerza(m["rp"], m["rp_ic_inf"], m["rp_ic_sup"]) if p_rs < 0.05
                        else "sin asociación distinguible de la nulidad con el diseño muestral"),
        })
    out = pd.DataFrame(filas)
    out["rp_formato"] = out.apply(
        lambda r: f"{r.rp:.2f} ({r.rp_ic_inf:.2f} – {r.rp_ic_sup:.2f})", axis=1)
    out["or_formato"] = out.apply(
        lambda r: f"{r['or']:.2f} ({r.or_ic_inf:.2f} – {r.or_ic_sup:.2f})", axis=1)
    return out.sort_values("rp", ascending=False).reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────
# 2. Medidas de impacto con pesos y bootstrap de diseño
# ─────────────────────────────────────────────────────────────────────


def _medidas_ponderadas(e: np.ndarray, y: np.ndarray, w: np.ndarray) -> dict[str, float]:
    """Prevalencias, RD y fracciones crudas con pesos, para una exposición."""
    w1, w0 = w * (e == 1), w * (e == 0)
    p1 = (w1 * y).sum() / w1.sum()
    p0 = (w0 * y).sum() / w0.sum()
    pe = w1.sum() / w.sum()
    rp = p1 / p0
    return {
        "pe": pe, "p1": p1, "p0": p0, "rd": (p1 - p0) * 100, "rp": rp,
        "afe": atr.fraccion_en_expuestos(rp),
        "paf": atr.paf_levin(pe, rp),
        "pc": (w1 * y).sum() / (w * y).sum(),
    }


def _ajustado(X: np.ndarray, y: np.ndarray, w: np.ndarray, start=None):
    """Poisson ponderado con enlace log: coeficientes idénticos a los de svy."""
    return sm.GLM(y, X, family=sm.families.Poisson(), freq_weights=w).fit(start_params=start)


def analizar(d: pd.DataFrame, predictores: list[str], exposiciones: list[str],
             nombre: str) -> pd.DataFrame:
    """Medidas de impacto crudas y ajustadas para un conjunto de exposiciones.

    ``d`` es la muestra de análisis ya con casos completos. Las fracciones
    ajustadas usan la RP del modelo con todas las covariables y la fórmula de
    Miettinen. Los intervalos de las fracciones salen del bootstrap de diseño;
    el de la RP ajustada, de la varianza de Taylor de ``svy``, que es la que se
    reporta en el resto del trabajo.
    """
    d = d.reset_index(drop=True)
    y = d.depresion_bin.to_numpy(float)
    w = d.peso.to_numpy(float)
    X, _ = mod.matriz_diseno(d, predictores, REFERENCIAS)
    X = sm.add_constant(X)
    columnas = list(X.columns)
    Xv = X.to_numpy(float)

    ajuste0 = _ajustado(Xv, y, w)
    rp_taylor = mod.razon_prevalencias_diseno(
        d, "depresion_bin", predictores, REFERENCIAS).set_index("termino")

    # Verificación: el ajuste ponderado coincide con el de svy
    for v in exposiciones:
        mia = float(np.exp(ajuste0.params[columnas.index(v)]))
        assert abs(mia - rp_taylor.loc[v, "rp"]) < 1e-4, (v, mia, rp_taylor.loc[v, "rp"])

    exp_arr = {v: d[v].to_numpy(int) for v in exposiciones}
    punto = {}
    for v in exposiciones:
        m = _medidas_ponderadas(exp_arr[v], y, w)
        rp_aj = float(np.exp(ajuste0.params[columnas.index(v)]))
        m["rp_aj"] = rp_aj
        m["afe_aj"] = atr.fraccion_en_expuestos(rp_aj)
        m["paf_aj"] = atr.paf_miettinen(m["pc"], rp_aj)
        punto[v] = m

    # Bootstrap de diseño (Rao y Wu)
    rep = atr.ReplicasRaoWu(d.estrato.to_numpy(), d.conglomerado.to_numpy(), cfg.RANDOM_SEED)
    claves = ["rd", "rp", "afe", "paf", "rp_aj", "afe_aj", "paf_aj"]
    boot = {v: {k: np.empty(N_REPLICAS) for k in claves} for v in exposiciones}
    for b in range(N_REPLICAS):
        wb = w * rep.factores()
        try:
            ab = _ajustado(Xv, y, wb, start=ajuste0.params)
        except Exception:  # réplica que no converge: se omite, no se inventa
            ab = None
        for v in exposiciones:
            m = _medidas_ponderadas(exp_arr[v], y, wb)
            if ab is not None:
                rp_aj = float(np.exp(ab.params[columnas.index(v)]))
                m["rp_aj"] = rp_aj
                m["afe_aj"] = atr.fraccion_en_expuestos(rp_aj)
                m["paf_aj"] = atr.paf_miettinen(m["pc"], rp_aj)
            else:
                m["rp_aj"] = m["afe_aj"] = m["paf_aj"] = np.nan
            for k in claves:
                boot[v][k][b] = m[k]

    filas = []
    for v in exposiciones:
        p = punto[v]
        ic = {k: atr.intervalo_percentil(boot[v][k]) for k in claves}
        t = rp_taylor.loc[v]
        filas.append({
            "muestra": nombre, "exposicion": ETIQUETA[v], "variable": v, "n": len(d),
            "prev_exposicion": p["pe"] * 100,
            "prev_expuestos": p["p1"] * 100, "prev_no_expuestos": p["p0"] * 100,
            "casos_expuestos_pct": p["pc"] * 100,
            "rd": p["rd"], "rd_ic_inf": ic["rd"][0], "rd_ic_sup": ic["rd"][1],
            "rp_cruda": p["rp"], "rp_cruda_ic_inf": ic["rp"][0], "rp_cruda_ic_sup": ic["rp"][1],
            "afe_cruda": p["afe"] * 100,
            "afe_cruda_ic_inf": ic["afe"][0] * 100, "afe_cruda_ic_sup": ic["afe"][1] * 100,
            "paf_cruda": p["paf"] * 100,
            "paf_cruda_ic_inf": ic["paf"][0] * 100, "paf_cruda_ic_sup": ic["paf"][1] * 100,
            "rp_ajustada": p["rp_aj"], "rp_ajustada_ic_inf": t.ic_inf,
            "rp_ajustada_ic_sup": t.ic_sup, "p_rp_ajustada": t.p,
            "rp_ajustada_boot_inf": ic["rp_aj"][0], "rp_ajustada_boot_sup": ic["rp_aj"][1],
            "afe_ajustada": p["afe_aj"] * 100,
            "afe_ajustada_ic_inf": atr.fraccion_en_expuestos(t.ic_inf) * 100,
            "afe_ajustada_ic_sup": atr.fraccion_en_expuestos(t.ic_sup) * 100,
            "paf_ajustada": p["paf_aj"] * 100,
            "paf_ajustada_ic_inf": ic["paf_aj"][0] * 100,
            "paf_ajustada_ic_sup": ic["paf_aj"][1] * 100,
        })
    return pd.DataFrame(filas)


def etiquetar_impacto(t: pd.DataFrame) -> pd.DataFrame:
    """Decide qué filas admiten una lectura de fracción atribuible.

    La fracción atribuible solo tiene lectura de «casos que no ocurrirían» si la
    razón de prevalencias ajustada es mayor que 1 con intervalo que no cruza 1.
    En los demás casos se conserva el número y se marca por qué no se interpreta.
    """
    def lectura(r) -> str:
        if r.rp_ajustada_ic_inf <= 1 <= r.rp_ajustada_ic_sup:
            return "Tras ajustar, no se distingue de la nulidad: no se interpreta fracción atribuible"
        if r.rp_ajustada < 1:
            return "Asociación protectora tras ajustar: la fracción es negativa y no se interpreta como casos evitables"
        return "Factor de riesgo tras ajustar: la fracción es lo que se evitaría solo si la asociación fuera causal"

    t = t.copy()
    t["lectura"] = t.apply(lectura, axis=1)
    t["interpretable"] = t.lectura.str.startswith("Factor de riesgo")
    return t


# ─────────────────────────────────────────────────────────────────────
# 3. Figura
# ─────────────────────────────────────────────────────────────────────


def figura_fuerza_e_impacto(t: pd.DataFrame) -> None:
    """Contrasta fuerza de asociación (RP) con impacto poblacional (PAF)."""
    viz.aplicar_tema()
    d = t[t.interpretable & (t.variable != "es_mujer")].sort_values("paf_ajustada")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 4.8), sharey=True)
    y = np.arange(len(d))

    a1.errorbar(d.rp_ajustada, y,
                xerr=[d.rp_ajustada - d.rp_ajustada_ic_inf, d.rp_ajustada_ic_sup - d.rp_ajustada],
                fmt="o", color=COL["navy"], capsize=3, markersize=7)
    a1.axvline(1, color=COL["gris"], linestyle="--", linewidth=1.2)
    a1.set_xscale("log")
    a1.xaxis.set_minor_locator(NullLocator())
    a1.xaxis.set_minor_formatter(NullFormatter())
    a1.set_xticks([1, 1.5, 2, 3, 5, 8])
    a1.set_xticklabels(["1", "1,5", "2", "3", "5", "8"])
    a1.set_yticks(y)
    a1.set_yticklabels([e.replace(" diagnosticada", "").replace("Consumo problemático de alcohol",
                                                                "Consumo problemático\nde alcohol")
                        for e in d.exposicion], fontsize=10)
    a1.set_xlabel("Razón de prevalencias ajustada (escala logarítmica)")
    a1.set_title("Qué tan fuerte es la asociación")

    a2.errorbar(d.paf_ajustada, y,
                xerr=[d.paf_ajustada - d.paf_ajustada_ic_inf, d.paf_ajustada_ic_sup - d.paf_ajustada],
                fmt="s", color=COL["dorado"], capsize=3, markersize=7)
    a2.axvline(0, color=COL["gris"], linewidth=1)
    a2.set_xlabel("Fracción atribuible poblacional ajustada (%)")
    a2.set_title("Cuántos casos de la población involucra")

    viz.pie_de_figura(
        fig, "Fuente: ENDES 2025 (INEI). Pesos de la encuesta; IC 95 % por bootstrap de conglomerados "
             "(RP: varianza de Taylor). La violencia se estima entre quienes tuvieron pareja. "
             "Son medidas basadas en prevalencia y no implican causalidad.")
    fig.tight_layout()
    dio.guardar_figura(fig, "fig_19_fuerza_e_impacto")
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────
# Orquestador
# ─────────────────────────────────────────────────────────────────────


def main() -> None:
    """Calcula las tablas 2×2, las medidas de impacto y la figura."""
    dio.configurar_logging()
    df = pd.read_parquet(cfg.DATASET_FINAL)
    base = df[df.en_analisis == 1].dropna(subset=["depresion_bin"]).copy()
    print(f"Población de análisis: {len(base):,}\n")

    # 1 · Tablas 2×2
    t2 = tabla_2x2_completa(base)
    dio.guardar_tabla(t2, "tabla_57_asociacion_2x2",
                      "Tabla 2×2, OR, razón de prevalencias y chi cuadrado por exposición")
    print("=" * 118)
    print("TABLAS 2×2 · a (expuestos con), b (expuestos sin), c (no expuestos con), d (no expuestos sin)")
    print("=" * 118)
    print(t2[["exposicion", "a", "b", "c", "d", "rp_formato", "or_formato", "chi2",
              "p_chi2", "p_rao_scott", "lectura"]].to_string(index=False))

    # Control cruzado con la tabla 12 (que usa Poisson robusto y Yates)
    t12 = pd.read_csv(cfg.TABLAS / "tabla_12_or_y_rp.csv", encoding="utf-8-sig").set_index("variable")
    dif = (t2.set_index("variable")[["or", "rp"]] - t12[["or", "rp"]]).abs().max()
    print(f"\nDiferencia máxima con la tabla 12 → OR: {dif['or']:.4f} · RP: {dif['rp']:.4f}")
    assert dif["or"] < 5e-3 and dif["rp"] < 5e-3, "la tabla 2×2 no cuadra con la tabla 12"

    # 2 · Medidas de impacto
    principal = base.dropna(subset=["depresion_bin", *COMPLETO]).copy()
    ppal = analizar(principal, COMPLETO,
                    [v for v, _ in EXPOSICIONES if v != "violencia_fisica"], "modelo principal")
    con_pareja = base[base.tuvo_pareja == 1].dropna(subset=[*COMPLETO, "violencia_fisica"]).copy()
    viol = analizar(con_pareja, [*COMPLETO, "violencia_fisica"], ["violencia_fisica"],
                    "población con pareja")
    imp = etiquetar_impacto(pd.concat([ppal, viol], ignore_index=True))
    imp = imp.sort_values("paf_ajustada", ascending=False).reset_index(drop=True)
    dio.guardar_tabla(imp, "tabla_58_riesgo_atribuible",
                      "Medidas de impacto basadas en prevalencia: crudas y ajustadas")

    print("\n" + "=" * 118)
    print("MEDIDAS DE IMPACTO BASADAS EN PREVALENCIA (pesos de la encuesta)")
    print("=" * 118)
    cols = ["exposicion", "prev_exposicion", "rd", "rp_cruda", "paf_cruda", "rp_ajustada",
            "afe_ajustada", "paf_ajustada", "paf_ajustada_ic_inf", "paf_ajustada_ic_sup"]
    with pd.option_context("display.float_format", "{:.2f}".format, "display.width", 200):
        print(imp[cols].to_string(index=False))
    print("\nControl: IC de la RP ajustada, Taylor frente a bootstrap")
    with pd.option_context("display.float_format", "{:.2f}".format, "display.width", 200):
        print(imp[["exposicion", "rp_ajustada_ic_inf", "rp_ajustada_ic_sup",
                   "rp_ajustada_boot_inf", "rp_ajustada_boot_sup"]].to_string(index=False))

    figura_fuerza_e_impacto(imp)
    print("\nAsociación y riesgo atribuible completados.")


if __name__ == "__main__":
    main()
