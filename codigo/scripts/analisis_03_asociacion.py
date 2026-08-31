"""Fase 2 · Asociación, sesgo y confusión (§11.2 del protocolo).

Tablas 2×2, OR crudo, razón de prevalencias por Poisson robusta, estratificación
con Mantel-Haenszel, criterio de confusión del 10 %, pruebas de homogeneidad
para modificación de efecto, ajuste por comparaciones múltiples y el DAG causal.

Uso
---
    python codigo/scripts/analisis_03_asociacion.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402
from depresion import (
    epi,  # noqa: E402
    viz,  # noqa: E402
)
from depresion import io as dio  # noqa: E402

C = cfg.COLORES

EXPOSICIONES = [
    ("violencia_fisica", "Violencia física de pareja", "Social"),
    ("consumo_frecuente", "Consumo frecuente de alcohol", "Conductual"),
    ("alcohol_problematico", "Consumo problemático de alcohol", "Conductual"),
    ("fuma_12m", "Fumó en los últimos 12 meses", "Conductual"),
    ("hta_dx", "Hipertensión diagnosticada", "Clínica"),
    ("diabetes_dx", "Diabetes diagnosticada", "Clínica"),
    ("obesidad", "Obesidad (IMC ≥ 30)", "Clínica"),
    ("es_mujer", "Sexo femenino", "Sociodemográfica"),
    ("es_rural", "Área rural", "Sociodemográfica"),
]

ESTRATIFICADORES = [("es_mujer", "Sexo"), ("grupo_etario", "Grupo etario"),
                    ("es_rural", "Área"), ("educacion_grupo", "Nivel educativo")]


# ─────────────────────────────────────────────────────────────────────
# OR crudo y razón de prevalencias
# ─────────────────────────────────────────────────────────────────────


def tabla_or_rp(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula OR crudo y RP para cada exposición, y compara ambos.

    En un transversal el OR sobreestima la RP tanto más cuanto mayor sea la
    prevalencia. Con 7 % de prevalencia deben parecerse; demostrarlo
    numéricamente es parte del rigor, no un trámite.
    """
    filas = []
    for v, etq, bloque in EXPOSICIONES:
        if v not in df.columns:
            continue
        r = epi.odds_ratio(df[v], df.depresion_bin)
        rp = epi.razon_prevalencias(df[v], df.depresion_bin)
        d = df[[v, "depresion_bin"]].dropna()
        prev_exp = d.loc[d[v] == 1, "depresion_bin"].mean() * 100
        prev_noexp = d.loc[d[v] == 0, "depresion_bin"].mean() * 100
        filas.append({
            "exposicion": etq, "variable": v, "bloque": bloque, "n": r["n"],
            "n_expuestos": int((d[v] == 1).sum()),
            "prev_expuestos": prev_exp, "prev_no_expuestos": prev_noexp,
            "diferencia_riesgo": prev_exp - prev_noexp,
            "or": r["or"], "or_ic_inf": r["ic_inf"], "or_ic_sup": r["ic_sup"],
            "rp": rp["rp"], "rp_ic_inf": rp["ic_inf"], "rp_ic_sup": rp["ic_sup"],
            "sobreestimacion_or_pct": (r["or"] - rp["rp"]) / rp["rp"] * 100,
            "p": r["p"], "celda_minima": r["celda_minima"], "advertencia": r["advertencia"],
        })
    out = pd.DataFrame(filas)
    out["p_fdr"] = epi.ajustar_p(out.p, "fdr_bh")
    out["p_bonferroni"] = epi.ajustar_p(out.p, "bonferroni")
    out["or_formato"] = out.apply(lambda r: epi.formato_ic(r.or_ic_inf and r["or"], r.or_ic_inf, r.or_ic_sup), axis=1)
    out["rp_formato"] = out.apply(lambda r: epi.formato_ic(r.rp, r.rp_ic_inf, r.rp_ic_sup), axis=1)
    return out.sort_values("or", ascending=False)


def guardar_tablas_2x2(df: pd.DataFrame) -> pd.DataFrame:
    """Exporta la tabla 2×2 de cada exposición, en formato largo."""
    filas = []
    for v, etq, _ in EXPOSICIONES:
        if v not in df.columns:
            continue
        t = epi.tabla_2x2(df[v], df.depresion_bin)
        for fila in t.index:
            filas.append({
                "exposicion": etq, "estado": fila,
                "sin_depresion": int(t.loc[fila, "Sin desenlace"]),
                "con_depresion": int(t.loc[fila, "Con desenlace"]),
                "total": int(t.loc[fila].sum()),
                "prevalencia_pct": t.loc[fila, "Con desenlace"] / t.loc[fila].sum() * 100,
            })
    return pd.DataFrame(filas)


# ─────────────────────────────────────────────────────────────────────
# Confusión y modificación de efecto
# ─────────────────────────────────────────────────────────────────────


def analisis_confusion(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evalúa confusión y modificación de efecto para cada par exposición-estrato."""
    filas, por_estrato = [], []
    for v, etq, _ in EXPOSICIONES:
        if v not in df.columns:
            continue
        for e, e_etq in ESTRATIFICADORES:
            if e == v:
                continue
            r = epi.mantel_haenszel(df[v], df.depresion_bin, df[e].astype(str))
            if "error" in r:
                continue
            filas.append({
                "exposicion": etq, "variable": v, "estratificador": e_etq,
                "or_crudo": r["or_crudo"], "or_mh": r["or_mh"],
                "mh_ic_inf": r["ic_inf"], "mh_ic_sup": r["ic_sup"],
                "cambio_pct": r["cambio_pct"], "p_homogeneidad": r["p_homogeneidad"],
                "confunde": r["hay_confusion"], "modifica_efecto": r["hay_interaccion"],
                "veredicto": r["veredicto"],
            })
            for pe in r["por_estrato"]:
                por_estrato.append({"exposicion": etq, "estratificador": e_etq, **pe})
    return pd.DataFrame(filas), pd.DataFrame(por_estrato)


# ─────────────────────────────────────────────────────────────────────
# Figuras
# ─────────────────────────────────────────────────────────────────────


def figura_or_vs_rp(t: pd.DataFrame) -> None:
    """Compara visualmente OR y RP para demostrar cuánto sobreestima el OR."""
    viz.aplicar_tema()
    d = t.dropna(subset=["rp"]).sort_values("or")
    fig, ax = plt.subplots(figsize=(9.5, 5.8))
    y = np.arange(len(d))
    ax.errorbar(d["or"], y + 0.14, xerr=[d["or"] - d.or_ic_inf, d.or_ic_sup - d["or"]],
                fmt="o", color=C["navy"], label="Odds ratio (OR)", markersize=6, capsize=3)
    ax.errorbar(d.rp, y - 0.14, xerr=[d.rp - d.rp_ic_inf, d.rp_ic_sup - d.rp],
                fmt="s", color=C["dorado"], label="Razón de prevalencias (RP)", markersize=6, capsize=3)
    ax.axvline(1, color=C["gris"], linestyle="--", linewidth=1.2)
    ax.set_yticks(y)
    ax.set_yticklabels(d.exposicion, fontsize=9.5)
    ax.set_xscale("log")
    ax.set_xlabel("Medida de asociación (escala logarítmica)")
    ax.set_title("Odds ratio frente a razón de prevalencias")
    ax.legend(loc="lower right")
    viz.pie_de_figura(
        fig, "Fuente: ENDES 2025 (INEI). Con prevalencia baja (7 %) ambas medidas convergen, "
             "como predice la teoría.")
    dio.guardar_figura(fig, "fig_06_or_vs_rp")
    plt.close(fig)


def figura_confusion(conf: pd.DataFrame) -> None:
    """Muestra el cambio porcentual entre OR crudo y ajustado."""
    viz.aplicar_tema()
    d = conf.copy()
    d["etiqueta"] = d.exposicion + " · " + d.estratificador
    d = d.reindex(d.cambio_pct.abs().sort_values().index).tail(18)
    fig, ax = plt.subplots(figsize=(9.5, max(6, 0.42 * len(d))))
    y = np.arange(len(d))
    colores = [C["rojo"] if abs(c) >= 10 else C["gris"] for c in d.cambio_pct]
    ax.barh(y, d.cambio_pct, color=colores, height=0.68)
    ax.axvline(10, color=C["rojo"], linestyle="--", linewidth=1.2)
    ax.axvline(-10, color=C["rojo"], linestyle="--", linewidth=1.2)
    ax.axvline(0, color=C["gris"], linewidth=1)
    ax.set_yticks(y)
    ax.set_yticklabels(d.etiqueta, fontsize=8.8)
    ax.set_xlabel("Cambio del OR crudo respecto al ajustado (%)")
    ax.set_title("Criterio de confusión: cambio del 10 %")
    viz.pie_de_figura(
        fig, "Fuente: ENDES 2025 (INEI). En rojo, los pares donde el ajuste cambia el "
             "estimador un 10 % o más: hay confusión.")
    dio.guardar_figura(fig, "fig_07_confusion")
    plt.close(fig)


def figura_dag() -> None:
    """Dibuja el DAG causal del estudio con matplotlib.

    Se dibuja a mano en lugar de con graphviz porque el binario ``dot`` no está
    instalado, y porque un DAG causal es una declaración de supuestos que
    conviene controlar posición a posición, no dejar a un algoritmo de layout.
    """
    viz.aplicar_tema()
    fig, ax = plt.subplots(figsize=(12, 8.2))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8.9)
    ax.axis("off")

    nodos = {
        "sexo":      (1.3, 6.6, "Sexo",                    C["navy"],   "confusor"),
        "edad":      (1.3, 5.1, "Edad",                    C["navy"],   "confusor"),
        "educacion": (1.3, 3.6, "Nivel\neducativo",        C["navy"],   "confusor"),
        "area":      (1.3, 2.1, "Área y\nregión",          C["navy"],   "confusor"),
        "alcohol":   (5.4, 6.9, "Consumo de\nalcohol",     C["dorado"], "exposición"),
        "tabaco":    (5.4, 5.3, "Tabaco",                  C["dorado"], "exposición"),
        "violencia": (5.4, 3.7, "Violencia\nde pareja",    C["dorado"], "exposición"),
        "cronicas":  (5.4, 2.1, "Condiciones\ncrónicas",   C["dorado"], "exposición"),
        "depresion": (9.6, 4.5, "DEPRESIÓN\nPHQ-9 ≥ 10",   C["rojo"],   "desenlace"),
        "tratam":    (9.6, 1.3, "Tratamiento\nrecibido",   C["gris"],   "consecuencia"),
    }
    for _, (x, y, etq, col, rol) in nodos.items():
        w, h = (1.9, 0.95) if rol != "desenlace" else (2.2, 1.05)
        ax.add_patch(plt.Rectangle((x - w / 2, y - h / 2), w, h, facecolor="white",
                                   edgecolor=col, linewidth=2.1, zorder=3,
                                   joinstyle="round"))
        ax.text(x, y, etq, ha="center", va="center", fontsize=10,
                fontweight="bold" if rol == "desenlace" else "normal",
                color=col, zorder=4, linespacing=1.3)

    def arco(a, b, color, estilo="-", curva=0.0, ancho=1.5, recorte_final=42):
        xa, ya = nodos[a][:2]
        xb, yb = nodos[b][:2]
        ax.add_patch(FancyArrowPatch(
            (xa, ya), (xb, yb), arrowstyle="-|>", mutation_scale=15,
            linewidth=ancho, color=color, linestyle=estilo, zorder=1,
            connectionstyle=f"arc3,rad={curva}", shrinkA=42, shrinkB=recorte_final))

    for conf in ["sexo", "edad", "educacion", "area"]:
        for expo in ["alcohol", "tabaco", "violencia", "cronicas"]:
            arco(conf, expo, C["gris_claro"], ancho=0.8)
        arco(conf, "depresion", C["navy"], curva=-0.28, ancho=1.3, recorte_final=68)
    for expo in ["alcohol", "tabaco", "violencia", "cronicas"]:
        arco(expo, "depresion", C["dorado"], ancho=2.1, recorte_final=68)
    arco("depresion", "tratam", C["rojo"], estilo="--", ancho=1.6)

    ax.text(0.2, 8.72, "DAG causal del estudio", fontsize=16, fontweight="bold",
            color=C["navy"], va="top")
    ax.text(0.2, 8.24,
            "Los supuestos causales se declaran antes de modelar; de aquí sale qué se ajusta.",
            fontsize=10, color=C["gris"], va="top")

    leyenda = [
        (C["navy"], "Confusor — se ajusta (criterio de puerta trasera)"),
        (C["dorado"], "Exposición de interés"),
        (C["rojo"], "Desenlace"),
        (C["gris"], "Consecuencia del desenlace — NO se ajusta (causalidad reversa)"),
    ]
    for i, (col, txt) in enumerate(leyenda):
        ax.add_patch(plt.Rectangle((0.35, 0.85 - i * 0.24), 0.28, 0.15,
                                   facecolor="white", edgecolor=col, linewidth=2))
        ax.text(0.78, 0.925 - i * 0.24, txt, fontsize=9, color=C["gris"], va="center")

    ax.text(11.85, 0.35,
            "No se ajusta por mediadores ni colisionadores aunque mejoren el ajuste.",
            fontsize=8.5, color=C["gris"], ha="right", style="italic")
    for ext in ("png", "pdf"):
        fig.savefig(cfg.DOCS / f"dag_causal.{ext}", dpi=cfg.DPI_FIGURAS,
                    bbox_inches="tight", facecolor="white")
    dio.guardar_figura(fig, "fig_08_dag_causal")
    plt.close(fig)


def main() -> None:
    """Ejecuta el análisis de asociación, confusión e interacción."""
    dio.configurar_logging()
    df = pd.read_parquet(cfg.DATASET_FINAL)
    base = df[df.en_analisis == 1].dropna(subset=["depresion_bin"]).copy()
    print(f"Población de análisis: {len(base):,}\n")

    t = tabla_or_rp(base)
    dio.guardar_tabla(t, "tabla_12_or_y_rp", "OR crudo y razón de prevalencias por exposición")
    print("=" * 110)
    print("OR CRUDO Y RAZÓN DE PREVALENCIAS")
    print("=" * 110)
    print(t[["exposicion", "n_expuestos", "prev_expuestos", "prev_no_expuestos",
             "or_formato", "rp_formato", "sobreestimacion_or_pct", "p_fdr"]].to_string(index=False))
    print(f"\nSobreestimación media del OR sobre la RP: {t.sobreestimacion_or_pct.abs().mean():.1f} %")

    t2 = guardar_tablas_2x2(base)
    dio.guardar_tabla(t2, "tabla_13_tablas_2x2", "Tablas 2×2 de cada exposición")

    conf, por_est = analisis_confusion(base)
    dio.guardar_tabla(conf, "tabla_14_confusion_mantel_haenszel",
                      "Confusión y modificación de efecto por Mantel-Haenszel")
    dio.guardar_tabla(por_est, "tabla_15_or_por_estrato", "OR específicos por estrato")

    print("\n" + "=" * 110)
    print("CONFUSIÓN (cambio ≥ 10 % entre OR crudo y ajustado)")
    print("=" * 110)
    hay = conf[conf.confunde].sort_values("cambio_pct", key=abs, ascending=False)
    print(hay[["exposicion", "estratificador", "or_crudo", "or_mh", "cambio_pct"]].to_string(index=False)
          if len(hay) else "  Ninguna combinación alcanza el umbral del 10 %.")

    print("\n" + "=" * 110)
    print("MODIFICACIÓN DE EFECTO (p de homogeneidad < 0,05)")
    print("=" * 110)
    inter = conf[conf.modifica_efecto].sort_values("p_homogeneidad")
    print(inter[["exposicion", "estratificador", "or_crudo", "or_mh", "p_homogeneidad"]].to_string(index=False)
          if len(inter) else "  Ninguna interacción significativa.")

    figura_or_vs_rp(t)
    figura_confusion(conf)
    figura_dag()
    print("\nAsociación completada.")


if __name__ == "__main__":
    main()
