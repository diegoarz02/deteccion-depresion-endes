"""Fase 2 · Regresión logística, modelo principal del estudio (§11.4).

Modelamiento por bloques (crudo, ajustado por sociodemográficas, completo),
con la versión de diseño complejo como inferencia principal y la versión sin
ponderar como sensibilidad. Incluye bondad de ajuste, discriminación,
calibración, linealidad del logit y forest plot.

Uso
---
    python codigo/scripts/analisis_05_logistica.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402
from depresion import io as dio  # noqa: E402
from depresion import modelos as mod  # noqa: E402
from depresion import viz  # noqa: E402

COL = cfg.COLORES

SOCIODEMOGRAFICAS = ["es_mujer", "grupo_etario", "educacion_grupo", "es_rural", "region_natural"]
EXPOSICIONES = ["consumo_frecuente", "alcohol_problematico", "fuma_12m",
                "hta_dx", "diabetes_dx", "obesidad"]
COMPLETO = SOCIODEMOGRAFICAS + EXPOSICIONES

REFERENCIAS = {
    "grupo_etario": "30-39",          # el grupo de menor prevalencia
    "educacion_grupo": "Superior",    # el de mayor nivel, como referencia
    "region_natural": "Costa",
}

ETIQUETAS_LEGIBLES = {
    "es_mujer": "Sexo femenino",
    "es_rural": "Área rural",
    "consumo_frecuente": "Consumo frecuente de alcohol",
    "alcohol_problematico": "Consumo problemático de alcohol",
    "fuma_12m": "Fumó en 12 meses",
    "hta_dx": "Hipertensión diagnosticada",
    "diabetes_dx": "Diabetes diagnosticada",
    "obesidad": "Obesidad (IMC ≥ 30)",
    "violencia_fisica": "Violencia física de pareja",
    "grupo_etario_15-19": "Edad 15-19 (ref. 30-39)",
    "grupo_etario_20-29": "Edad 20-29 (ref. 30-39)",
    "grupo_etario_40-49": "Edad 40-49 (ref. 30-39)",
    "grupo_etario_50-59": "Edad 50-59 (ref. 30-39)",
    "grupo_etario_60+": "Edad 60+ (ref. 30-39)",
    "educacion_grupo_Primaria o menos": "Primaria o menos (ref. Superior)",
    "educacion_grupo_Secundaria": "Secundaria (ref. Superior)",
    "region_natural_Sierra": "Sierra (ref. Costa)",
    "region_natural_Selva": "Selva (ref. Costa)",
}


def bloques(df: pd.DataFrame) -> pd.DataFrame:
    """Ajusta los tres bloques de modelos y compara los OR de cada exposición."""
    filas = []
    for v in EXPOSICIONES:
        r1 = mod.logistica(df, "depresion_bin", [v], con_diseno=True)
        t1 = r1["tabla_or"].iloc[0]
        r2 = mod.logistica(df, "depresion_bin", [v, *SOCIODEMOGRAFICAS],
                           con_diseno=True, referencias=REFERENCIAS)
        t2 = r2["tabla_or"].set_index("termino").loc[v]
        filas.append({
            "exposicion": ETIQUETAS_LEGIBLES.get(v, v), "variable": v,
            "or_crudo": t1["or"], "crudo_ic_inf": t1.ic_inf, "crudo_ic_sup": t1.ic_sup,
            "p_crudo": t1.p,
            "or_ajustado": t2["or"], "ajustado_ic_inf": t2.ic_inf, "ajustado_ic_sup": t2.ic_sup,
            "p_ajustado": t2.p,
            "cambio_pct": (t1["or"] - t2["or"]) / t2["or"] * 100,
            "cambia_de_direccion": (t1["or"] - 1) * (t2["or"] - 1) < 0,
        })
    return pd.DataFrame(filas)


def figura_forest(tabla: pd.DataFrame, nombre: str, titulo: str) -> None:
    """Forest plot de los OR ajustados con su intervalo de confianza."""
    viz.aplicar_tema()
    d = tabla.copy()
    d["etq"] = d.termino.map(lambda t: ETIQUETAS_LEGIBLES.get(t, t))
    d = d.sort_values("or")
    fig, ax = plt.subplots(figsize=(10, max(6, 0.42 * len(d))))
    y = np.arange(len(d))
    colores = [COL["rojo"] if r.ic_inf > 1 else (COL["verde"] if r.ic_sup < 1 else COL["gris"])
               for _, r in d.iterrows()]
    # errorbar solo admite un color por llamada, así que cada intervalo se
    # dibuja por separado para poder colorearlo según su significación.
    for yi, (_, r), col in zip(y, d.iterrows(), colores, strict=False):
        ax.errorbar(r["or"], yi, xerr=[[r["or"] - r.ic_inf], [r.ic_sup - r["or"]]],
                    fmt="none", ecolor=col, elinewidth=1.8, capsize=3.5)
    ax.scatter(d["or"], y, color=colores, s=46, zorder=4)
    ax.axvline(1, color=COL["navy"], linestyle="--", linewidth=1.3)
    ax.set_yticks(y)
    ax.set_yticklabels(d.etq, fontsize=9.5)
    ax.set_xscale("log")
    ax.set_xlabel("Odds ratio ajustado (escala logarítmica) · IC 95 %")
    ax.set_title(titulo)
    for yi, (_, r) in zip(y, d.iterrows(), strict=False):
        ax.text(ax.get_xlim()[1] * 0.99, yi, f"{r['or']:.2f} ({r.ic_inf:.2f}–{r.ic_sup:.2f})",
                va="center", ha="right", fontsize=8.2, color=COL["gris"])
    viz.pie_de_figura(
        fig, "Fuente: ENDES 2025 (INEI). Rojo: asociación positiva; verde: negativa; "
             "gris: intervalo que cruza el 1.")
    dio.guardar_figura(fig, nombre)
    plt.close(fig)


def figura_roc_calibracion(y, p, hl: dict, disc: dict, curva: pd.DataFrame, cal: dict) -> None:
    """Panel con curva ROC y curva de calibración."""
    viz.aplicar_tema()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.6))

    a1.plot(disc["fpr"], disc["tpr"], color=COL["navy"], linewidth=2.2)
    a1.plot([0, 1], [0, 1], color=COL["gris"], linestyle="--", linewidth=1.2)
    a1.fill_between(disc["fpr"], disc["tpr"], alpha=0.12, color=COL["navy"])
    a1.set_xlabel("1 − especificidad")
    a1.set_ylabel("Sensibilidad")
    a1.set_title("Curva ROC")
    a1.text(0.62, 0.13, f"AUC = {disc['auc']:.3f}\nIC 95 % ({disc['ic_inf']:.3f}–{disc['ic_sup']:.3f})\n"
                        f"{disc['veredicto']}",
            transform=a1.transAxes, fontsize=10, color=COL["navy"],
            bbox={"boxstyle": "round,pad=0.5", "facecolor": "#F7F9FC", "edgecolor": COL["gris_claro"]})

    a2.plot([0, curva.p_media.max() * 1.05], [0, curva.p_media.max() * 1.05],
            color=COL["gris"], linestyle="--", linewidth=1.2, label="Calibración perfecta")
    a2.plot(curva.p_media, curva.observado, "o-", color=COL["dorado"], linewidth=2, markersize=7,
            label="Modelo")
    a2.set_xlabel("Probabilidad predicha media")
    a2.set_ylabel("Proporción observada")
    a2.set_title("Curva de calibración por deciles de riesgo")
    a2.legend(loc="upper left")
    a2.text(0.97, 0.06, f"Brier = {cal['brier']:.4f}\nnulo = {cal['brier_referencia']:.4f}\n"
                        f"mejora {cal['skill_score'] * 100:.1f} %\nHosmer-Lemeshow p = {hl['p']:.4f}",
            transform=a2.transAxes, ha="right", fontsize=9.5, color=COL["gris"],
            bbox={"boxstyle": "round,pad=0.5", "facecolor": "#F7F9FC", "edgecolor": COL["gris_claro"]})

    fig.suptitle("Discriminación y calibración del modelo logístico", fontsize=14,
                 fontweight="bold", color=COL["navy"], y=1.02)
    viz.pie_de_figura(fig)
    dio.guardar_figura(fig, "fig_12_roc_calibracion")
    plt.close(fig)


def main() -> None:
    """Ejecuta el modelamiento logístico completo."""
    dio.configurar_logging()
    df = pd.read_parquet(cfg.DATASET_FINAL)
    base = df[df.en_analisis == 1].dropna(subset=["depresion_bin"]).copy()
    print(f"Población de análisis: {len(base):,}\n")

    # ── Bloques ───────────────────────────────────────────────────
    bl = bloques(base)
    dio.guardar_tabla(bl, "tabla_21_modelos_por_bloques",
                      "OR crudo frente a ajustado por sociodemográficas")
    print("=" * 104)
    print("MODELAMIENTO POR BLOQUES — crudo frente a ajustado")
    print("=" * 104)
    print(bl[["exposicion", "or_crudo", "or_ajustado", "cambio_pct",
              "cambia_de_direccion", "p_ajustado"]].to_string(index=False))

    # ── Modelo completo con diseño complejo ───────────────────────
    r = mod.logistica(base, "depresion_bin", COMPLETO, con_diseno=True, referencias=REFERENCIAS)
    tabla = r["tabla_or"]
    # La etiqueta legible viaja con la tabla para que el boletín y el informe no
    # tengan que reconstruirla a partir del nombre técnico del término.
    tabla["etiqueta_legible"] = tabla.termino.map(lambda t: ETIQUETAS_LEGIBLES.get(t, t))
    dio.guardar_tabla(tabla, "tabla_22_logistica_diseno_complejo",
                      "Modelo logístico completo con diseño muestral complejo")

    print("\n" + "=" * 104)
    print(f"MODELO COMPLETO — diseño complejo · n = {r['n']:,} · eventos = {r['eventos']:,} · "
          f"EPV = {r['epv']:.1f}")
    print("=" * 104)
    t = tabla.copy()
    t["etq"] = t.termino.map(lambda x: ETIQUETAS_LEGIBLES.get(x, x))
    print(t[["etq", "or_formato", "p", "significativo"]].to_string(index=False))

    # ── Sensibilidad: sin ponderar ────────────────────────────────
    r_sp = mod.logistica(base, "depresion_bin", COMPLETO, con_diseno=False, referencias=REFERENCIAS)
    comp = tabla[["termino", "or", "ic_inf", "ic_sup", "p"]].merge(
        r_sp["tabla_or"][["termino", "or", "ic_inf", "ic_sup", "p"]],
        on="termino", suffixes=("_diseno", "_sin_ponderar"))
    comp["cambio_pct"] = (comp.or_diseno - comp.or_sin_ponderar) / comp.or_sin_ponderar * 100
    comp["etiqueta"] = comp.termino.map(lambda x: ETIQUETAS_LEGIBLES.get(x, x))
    dio.guardar_tabla(comp, "tabla_23_sensibilidad_diseno_vs_sin_ponderar",
                      "Comparación del modelo con y sin diseño muestral")
    print("\n" + "=" * 104)
    print("SENSIBILIDAD — con diseño frente a sin ponderar")
    print("=" * 104)
    print(comp[["etiqueta", "or_diseno", "or_sin_ponderar", "cambio_pct"]].to_string(index=False))
    print(f"\nCambio absoluto medio del OR: {comp.cambio_pct.abs().mean():.2f} %  |  "
          f"máximo: {comp.cambio_pct.abs().max():.2f} %")

    # ── Diagnóstico del modelo ────────────────────────────────────
    p_pred = r["p_pred"]
    y = r["y"].values
    hl = mod.hosmer_lemeshow(y, p_pred)
    disc = mod.discriminacion(y, p_pred)
    curva, cal = mod.calibracion(y, p_pred)
    # El modelo de diseño NO usa class_weight, así que sus probabilidades sí están
    # calibradas a la prevalencia real y el corte en la prevalencia es legítimo.
    met = mod.metricas_clasificacion(y, p_pred, umbral="prevalencia")
    bt = mod.linealidad_logit(base, "depresion_bin", "edad")

    diag = pd.DataFrame([
        {"aspecto": "Eventos por variable (EPV)", "valor": f"{r['epv']:.1f}",
         "veredicto": "Holgado" if r["epv"] >= 10 else "Insuficiente"},
        {"aspecto": "Discriminación (AUC)",
         "valor": f"{disc['auc']:.3f} ({disc['ic_inf']:.3f}–{disc['ic_sup']:.3f})",
         "veredicto": disc["veredicto"]},
        {"aspecto": "Bondad de ajuste (Hosmer-Lemeshow)",
         "valor": f"χ² = {hl['chi2']:.2f}, gl = {hl['gl']}, p = {hl['p']:.4f}",
         "veredicto": hl["veredicto"]},
        {"aspecto": "Calibración (Brier)", "valor": f"{cal['brier']:.4f}",
         "veredicto": cal["veredicto"]},
        {"aspecto": "Linealidad del logit en edad (Box-Tidwell)",
         "valor": f"p = {bt['p_box_tidwell']:.4f}", "veredicto": bt["veredicto"]},
        {"aspecto": "Sensibilidad (corte en la prevalencia)",
         "valor": f"{met['sensibilidad']:.3f}",
         "veredicto": f"Umbral {met['umbral']:.4f}; el modelo está calibrado, así que "
                      f"el corte en la prevalencia es interpretable"},
        {"aspecto": "Especificidad (mismo corte)", "valor": f"{met['especificidad']:.3f}",
         "veredicto": "Compromiso propio de un tamizaje: capta más casos a costa de más falsos positivos"},
        {"aspecto": "AUC-PR", "valor": f"{met['auc_pr']:.4f}",
         "veredicto": f"Frente a {met['prevalencia']:.4f} del azar: "
                      f"{met['auc_pr'] / met['prevalencia']:.1f} veces mejor"},
        {"aspecto": "Exactitud del modelo trivial",
         "valor": f"{met['exactitud_modelo_trivial']:.3f}",
         "veredicto": "Referencia obligada: predecir 'nadie' acierta el 93 %"},
    ])
    dio.guardar_tabla(diag, "tabla_24_diagnostico_logistica",
                      "Diagnóstico del modelo logístico")
    dio.guardar_tabla(curva, "tabla_25_curva_calibracion", "Curva de calibración por deciles")
    print("\n" + "=" * 104)
    print("DIAGNÓSTICO DEL MODELO")
    print("=" * 104)
    with pd.option_context("display.max_colwidth", 78):
        print(diag.to_string(index=False))

    # ── Sensibilidad: corte PHQ ≥ 5 y subpoblación con pareja ─────
    r5 = mod.logistica(base, "depresion_leve_bin", COMPLETO, con_diseno=True, referencias=REFERENCIAS)
    con_pareja = base[base.tuvo_pareja == 1]
    rv = mod.logistica(con_pareja, "depresion_bin", [*COMPLETO, "violencia_fisica"],
                       con_diseno=True, referencias=REFERENCIAS)
    dio.guardar_tabla(r5["tabla_or"], "tabla_26_sensibilidad_corte5",
                      "Modelo logístico con corte PHQ-9 ≥ 5")
    rv["tabla_or"]["etiqueta_legible"] = rv["tabla_or"].termino.map(
        lambda t: ETIQUETAS_LEGIBLES.get(t, t))
    dio.guardar_tabla(rv["tabla_or"], "tabla_27_modelo_subpoblacion_violencia",
                      "Modelo en la subpoblación con pareja, incluyendo violencia física")
    print(f"\nSubpoblación con pareja: n = {rv['n']:,}, eventos = {rv['eventos']:,}")
    viol = rv["tabla_or"].set_index("termino").loc["violencia_fisica"]
    print(f"  OR ajustado de violencia física: {viol['or']:.2f} "
          f"({viol.ic_inf:.2f} – {viol.ic_sup:.2f}), p = {viol.p:.2e}")

    # ── Figuras y exportación ─────────────────────────────────────
    figura_forest(tabla, "fig_11_forest_or_ajustados",
                  "Odds ratios ajustados — modelo completo con diseño complejo")
    figura_forest(rv["tabla_or"], "fig_11b_forest_subpoblacion",
                  "Odds ratios ajustados — subpoblación con pareja")
    figura_roc_calibracion(y, p_pred, hl, disc, curva, cal)

    # Coeficientes para el simulador del boletín (§12) y para la API (§13)
    coefs = {
        "intercepto": float(r["intercepto"]),
        "coeficientes": {row.termino: float(row.coeficiente)
                         for _, row in r["tabla_or"].iterrows()},
        "etiquetas": r["etiquetas"],
        "referencias": REFERENCIAS,
        "auc": float(disc["auc"]),
        "brier": float(cal["brier"]),
        "prevalencia": float(y.mean()),
        "n": int(r["n"]),
        "variables_modelo": COMPLETO,
        "disclaimer": cfg.DISCLAIMER,
    }
    destino = cfg.MODELOS / "coeficientes_logistico.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(coefs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nCoeficientes exportados a {destino.name}")
    print("\nRegresión logística completada.")


if __name__ == "__main__":
    main()
