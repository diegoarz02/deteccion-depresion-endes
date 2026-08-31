"""Fase 2 · Efecto total frente a directo, interacciones e imputación (§4 de la 2.ª corrida).

Tres cosas que la primera corrida dejó abiertas:

**1. ¿La obesidad es confusora o mediadora?** El DAG lo resuelve: si el alcohol
y el tabaco causan obesidad, y la obesidad causa depresión, entonces la obesidad
está *en la ruta* que queremos medir. Ajustar por ella bloquea parte del efecto.
Por eso se reportan dos modelos y la diferencia entre ellos es, en sí misma, el
resultado:

- **Modelo A — efecto TOTAL:** sin obesidad ni IMC en el ajuste.
- **Modelo B — efecto DIRECTO:** con ellos, bloqueando la ruta corporal.

**2. Interacciones.** Con N ≈ 30 000, Breslow-Day declara significativas
diferencias irrelevantes. Se exige que cumplan las tres condiciones: p ajustado
por FDR, razón de OR entre estratos con magnitud apreciable, y n suficiente en
ambos estratos.

**3. Imputación múltiple** como análisis de sensibilidad, aunque los faltantes
estén por debajo del 5 %.

Uso
---
    python codigo/scripts/analisis_08_mediacion.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402
from depresion import (
    epi,  # noqa: E402
    viz,  # noqa: E402
)
from depresion import io as dio  # noqa: E402
from depresion import modelos as mod  # noqa: E402

COL = cfg.COLORES

CONFUSORES = ["es_mujer", "grupo_etario", "educacion_grupo", "es_rural", "region_natural"]
EXPOSICIONES = ["consumo_frecuente", "alcohol_problematico", "fuma_12m",
                "hta_dx", "diabetes_dx"]
MEDIADORES = ["obesidad"]

REFERENCIAS = {"grupo_etario": "30-39", "educacion_grupo": "Superior",
               "region_natural": "Costa"}

ETIQUETAS = {
    "es_mujer": "Sexo femenino", "es_rural": "Área rural",
    "consumo_frecuente": "Consumo frecuente de alcohol",
    "alcohol_problematico": "Consumo problemático de alcohol",
    "fuma_12m": "Fumó en 12 meses", "hta_dx": "Hipertensión diagnosticada",
    "diabetes_dx": "Diabetes diagnosticada", "obesidad": "Obesidad (IMC ≥ 30)",
    "altitud_100m": "Altitud (por 100 m)",
}


# ─────────────────────────────────────────────────────────────────────
# 1. Efecto total frente a efecto directo
# ─────────────────────────────────────────────────────────────────────


def modelos_mediacion(d: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    r"""Ajusta los modelos A (efecto total) y B (efecto directo) y los compara.

    La proporción mediada se calcula en la escala del logaritmo del OR, que es
    donde el modelo es aditivo:

    .. math:: \text{proporción mediada} = 1 - \frac{\ln(OR_{directo})}{\ln(OR_{total})}

    Es una aproximación: la descomposición exacta en un modelo logístico exige
    supuestos adicionales (no confusión de la relación mediador-desenlace, entre
    otros) y con desenlace no raro sufre el problema de la no colapsabilidad del
    OR. Se reporta como orden de magnitud, no como estimación puntual precisa.
    """
    r_a = mod.logistica(d, "depresion_bin", [*EXPOSICIONES, *CONFUSORES],
                        con_diseno=True, referencias=REFERENCIAS)
    r_b = mod.logistica(d, "depresion_bin", [*EXPOSICIONES, *CONFUSORES, *MEDIADORES],
                        con_diseno=True, referencias=REFERENCIAS)

    a = r_a["tabla_or"].set_index("termino")
    b = r_b["tabla_or"].set_index("termino")

    filas = []
    for v in EXPOSICIONES:
        if v not in a.index or v not in b.index:
            continue
        or_t, or_d = a.loc[v, "or"], b.loc[v, "or"]
        ln_t, ln_d = np.log(or_t), np.log(or_d)
        prop = (1 - ln_d / ln_t) * 100 if abs(ln_t) > 1e-9 else np.nan
        # La proporción mediada solo tiene lectura si ambos efectos van en el
        # mismo sentido y el total no es prácticamente nulo.
        interpretable = (ln_t * ln_d > 0) and abs(ln_t) > 0.05
        filas.append({
            "exposicion": ETIQUETAS.get(v, v), "variable": v,
            "or_total": or_t, "total_ic_inf": a.loc[v, "ic_inf"],
            "total_ic_sup": a.loc[v, "ic_sup"], "p_total": a.loc[v, "p"],
            "or_directo": or_d, "directo_ic_inf": b.loc[v, "ic_inf"],
            "directo_ic_sup": b.loc[v, "ic_sup"], "p_directo": b.loc[v, "p"],
            "cambio_pct": (or_t - or_d) / or_d * 100,
            "proporcion_mediada_pct": prop if interpretable else np.nan,
            "interpretable": interpretable,
        })
    tabla = pd.DataFrame(filas)
    tabla["or_total_fmt"] = tabla.apply(
        lambda r: f"{r.or_total:.2f} ({r.total_ic_inf:.2f}–{r.total_ic_sup:.2f})", axis=1)
    tabla["or_directo_fmt"] = tabla.apply(
        lambda r: f"{r.or_directo:.2f} ({r.directo_ic_inf:.2f}–{r.directo_ic_sup:.2f})", axis=1)
    tabla["lectura"] = np.where(
        ~tabla.interpretable,
        "Efecto total demasiado cercano al nulo: la proporción mediada no tiene lectura",
        np.where(tabla.proporcion_mediada_pct.abs() < 5,
                 "Sin mediación apreciable por la vía corporal",
                 "Parte del efecto pasa por la obesidad"))
    return tabla, {"A": r_a, "B": r_b}


def verificar_supuesto_mediacion(d: pd.DataFrame) -> pd.DataFrame:
    """Comprueba el primer eslabón del DAG: si las exposiciones predicen la obesidad.

    Si el alcohol o el tabaco no se asocian con la obesidad, la ruta mediadora
    no existe y toda la discusión sobre efecto directo frente a total es
    innecesaria para esa exposición. Es la comprobación que hace honesto el
    análisis de mediación.
    """
    filas = []
    for v in EXPOSICIONES:
        r = mod.logistica(d, "obesidad", [v, *CONFUSORES], con_diseno=True,
                          referencias=REFERENCIAS)
        t = r["tabla_or"].set_index("termino").loc[v]
        filas.append({
            "exposicion": ETIQUETAS.get(v, v), "variable": v,
            "or_hacia_obesidad": t["or"], "ic_inf": t.ic_inf, "ic_sup": t.ic_sup,
            "p": t.p,
            "hay_primer_eslabon": bool(t.p < 0.05),
        })
    out = pd.DataFrame(filas)
    out["veredicto"] = np.where(
        out.hay_primer_eslabon,
        "La exposición se asocia con la obesidad: la ruta mediadora es plausible",
        "Sin asociación con la obesidad: no hay ruta que mediar")
    return out


def figura_mediacion(tabla: pd.DataFrame) -> None:
    """Compara lado a lado el efecto total y el directo."""
    viz.aplicar_tema()
    d = tabla.sort_values("or_total")
    fig, ax = plt.subplots(figsize=(10, max(5, 0.85 * len(d))))
    y = np.arange(len(d))
    ax.errorbar(d.or_total, y + 0.13,
                xerr=[d.or_total - d.total_ic_inf, d.total_ic_sup - d.or_total],
                fmt="o", color=COL["navy"], markersize=8, capsize=3.5,
                label="Modelo A · efecto total (sin obesidad)")
    ax.errorbar(d.or_directo, y - 0.13,
                xerr=[d.or_directo - d.directo_ic_inf, d.directo_ic_sup - d.or_directo],
                fmt="s", color=COL["dorado"], markersize=8, capsize=3.5,
                label="Modelo B · efecto directo (con obesidad)")
    ax.axvline(1, color=COL["gris"], linestyle="--", linewidth=1.3)
    ax.set_yticks(y)
    ax.set_yticklabels(d.exposicion, fontsize=10)
    ax.set_xscale("log")
    ax.set_xlabel("Odds ratio ajustado (escala logarítmica)")
    ax.set_title("Efecto total frente a efecto directo")
    ax.legend(loc="lower right", fontsize=9.5)
    viz.pie_de_figura(
        fig, "Fuente: ENDES 2025 (INEI). La distancia entre ambos puntos es la parte del "
             "efecto que viaja por la ruta corporal.")
    dio.guardar_figura(fig, "fig_17_mediacion")
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────
# 2. Interacciones con filtro de magnitud
# ─────────────────────────────────────────────────────────────────────

RAZON_MINIMA = 1.5      # la razón entre los OR de los estratos
EVENTOS_MINIMOS = 30    # por celda (estrato × nivel de exposición)


def interacciones_filtradas(d: pd.DataFrame) -> pd.DataFrame:
    """Evalúa las interacciones con los tres criterios exigidos.

    Un valor p pequeño con N grande no dice que la modificación de efecto sea
    relevante: dice que la muestra es grande. Se exige, además de la
    significación corregida por comparaciones múltiples, que los OR de los
    estratos difieran de forma apreciable y que ambos estratos tengan casos
    suficientes para estimar.
    """
    estratificadores = [("es_mujer", "Sexo"), ("grupo_etario", "Grupo etario"),
                        ("es_rural", "Área"), ("educacion_grupo", "Nivel educativo"),
                        ("altitud_categoria", "Piso altitudinal")]
    filas = []
    for v in [*EXPOSICIONES, *MEDIADORES]:
        for e, e_etq in estratificadores:
            if e == v or v not in d.columns or e not in d.columns:
                continue
            r = epi.mantel_haenszel(d[v], d.depresion_bin, d[e].astype(str))
            if "error" in r or not r.get("por_estrato"):
                continue
            ors = [x["or"] for x in r["por_estrato"] if np.isfinite(x["or"]) and x["or"] > 0]
            if len(ors) < 2:
                continue
            razon = max(ors) / min(ors)
            # Recuento de eventos por celda (estrato × nivel de exposición). No basta
            # con contarlos por estrato: lo que se compara entre estratos es un OR, y
            # un estrato con 200 eventos pero solo 2 entre los expuestos da un OR tan
            # inestable como uno con 10 eventos en total. La celda es la unidad que
            # limita la estimación, así que es la que hay que exigir.
            sub = d.dropna(subset=[v, e, "depresion_bin"])
            reales = (sub.groupby([sub[e].astype(str), sub[v].astype(str)],
                                  observed=True).depresion_bin.sum().astype(int).tolist())
            filas.append({
                "exposicion": ETIQUETAS.get(v, v), "variable": v,
                "estratificador": e_etq,
                "or_crudo": r["or_crudo"], "or_mh": r["or_mh"],
                "or_minimo_estrato": min(ors), "or_maximo_estrato": max(ors),
                "razon_or": razon,
                "eventos_min_celda": min(reales) if reales else 0,
                "p_homogeneidad": r["p_homogeneidad"],
            })
    out = pd.DataFrame(filas)
    if out.empty:
        return out
    out["p_fdr"] = epi.ajustar_p(out.p_homogeneidad, "fdr_bh")

    out["criterio_1_p_fdr"] = out.p_fdr < 0.05
    out["criterio_2_magnitud"] = (out.razon_or >= RAZON_MINIMA) | (out.razon_or <= 1 / RAZON_MINIMA)
    out["criterio_3_eventos"] = out.eventos_min_celda >= EVENTOS_MINIMOS
    out["sobrevive"] = out.criterio_1_p_fdr & out.criterio_2_magnitud & out.criterio_3_eventos
    out["veredicto"] = np.where(
        out.sobrevive,
        "Modificación de efecto relevante: reportar OR por estrato",
        np.where(out.criterio_1_p_fdr & ~out.criterio_2_magnitud,
                 f"Significativa pero irrelevante: los OR difieren menos de {RAZON_MINIMA}×",
                 np.where(~out.criterio_1_p_fdr, "No significativa tras corregir por FDR",
                          "Estratos con muy pocos eventos")))
    return out.sort_values("p_fdr")


# ─────────────────────────────────────────────────────────────────────
# 3. Imputación múltiple
# ─────────────────────────────────────────────────────────────────────


def imputacion_multiple(d: pd.DataFrame, m_imputaciones: int = 5) -> pd.DataFrame:
    """Compara el modelo de casos completos con el de imputación múltiple.

    Los estimadores se combinan con las reglas de Rubin, que suman la varianza
    dentro de cada imputación y la varianza entre imputaciones. Si las
    conclusiones no cambian, el análisis de casos completos queda respaldado.
    """
    from sklearn.experimental import enable_iterative_imputer  # noqa: F401
    from sklearn.impute import IterativeImputer

    variables = [*EXPOSICIONES, *CONFUSORES, *MEDIADORES]
    base = d[["depresion_bin", "peso", "conglomerado", "estrato", *variables]].copy()

    faltantes = base[variables].isna().mean() * 100
    log_faltantes = faltantes[faltantes > 0].round(2)


    # Matriz numérica para el imputador.
    #
    # `drop_first=True` es imprescindible: con todas las indicadoras de un
    # factor, las columnas suman uno y la matriz de diseño queda singular. El
    # ajuste devolvería errores estándar NaN y los intervalos se desbordarían
    # al exponenciar.
    X = pd.get_dummies(base[variables], dummy_na=False, drop_first=True).astype(float)
    X = X.loc[:, X.std() > 0]                     # descarta columnas constantes
    columnas = list(X.columns)
    estimaciones, varianzas = [], []

    for i in range(m_imputaciones):
        imp = IterativeImputer(max_iter=10, random_state=cfg.RANDOM_SEED + i,
                               sample_posterior=True)
        Xi = pd.DataFrame(imp.fit_transform(X), columns=columnas, index=base.index)
        # Las binarias vuelven a ser 0/1; las categóricas ya son indicadoras
        for c in columnas:
            if set(X[c].dropna().unique()) <= {0.0, 1.0}:
                Xi[c] = (Xi[c] >= 0.5).astype(float)
        di = base[["depresion_bin", "peso", "conglomerado", "estrato"]].join(Xi)
        di = di.dropna(subset=["depresion_bin"])
        r = mod.logistica(di, "depresion_bin", columnas, con_diseno=True)
        t = r["tabla_or"].set_index("termino")
        estimaciones.append(t.coeficiente)
        varianzas.append(t.ee ** 2)

    # El modelo de referencia usa exactamente la misma parametrización que los
    # imputados, para que la comparación sea de la imputación y no del diseño
    # de la matriz.
    completos = base[["depresion_bin", "peso", "conglomerado", "estrato"]].join(X).dropna()
    r_cc = mod.logistica(completos, "depresion_bin", columnas, con_diseno=True)
    cc = r_cc["tabla_or"].set_index("termino")

    E = pd.concat(estimaciones, axis=1)
    V = pd.concat(varianzas, axis=1)
    q_barra = E.mean(axis=1)                       # estimador combinado
    u_barra = V.mean(axis=1)                       # varianza intra
    b = E.var(axis=1, ddof=1)                      # varianza entre
    t_total = u_barra + (1 + 1 / m_imputaciones) * b
    se = np.sqrt(t_total)

    filas = []
    for termino in q_barra.index:
        if termino not in cc.index:
            continue
        filas.append({
            "termino": termino, "etiqueta": ETIQUETAS.get(termino, termino),
            "or_casos_completos": cc.loc[termino, "or"],
            "cc_ic_inf": cc.loc[termino, "ic_inf"], "cc_ic_sup": cc.loc[termino, "ic_sup"],
            "or_imputado": np.exp(q_barra[termino]),
            "imp_ic_inf": np.exp(q_barra[termino] - 1.96 * se[termino]),
            "imp_ic_sup": np.exp(q_barra[termino] + 1.96 * se[termino]),
            "cambio_pct": (cc.loc[termino, "or"] - np.exp(q_barra[termino]))
                          / np.exp(q_barra[termino]) * 100,
            "fraccion_informacion_perdida": float(
                ((1 + 1 / m_imputaciones) * b[termino]) / t_total[termino]),
        })
    out = pd.DataFrame(filas)
    out["conclusion_cambia"] = (
        (out.cc_ic_inf > 1) != (out.imp_ic_inf > 1)) | ((out.cc_ic_sup < 1) != (out.imp_ic_sup < 1))
    out.attrs["faltantes"] = log_faltantes.to_dict()
    out.attrs["m"] = m_imputaciones
    return out


def main() -> None:
    """Ejecuta mediación, interacciones e imputación."""
    dio.configurar_logging()
    df = pd.read_parquet(cfg.DATASET_FINAL)
    d = df[df.en_analisis == 1].dropna(subset=["depresion_bin"]).copy()
    print(f"Población de análisis: {len(d):,}\n")

    # ── 1. Mediación ──────────────────────────────────────────────
    print("=" * 100)
    print("PRIMER ESLABÓN DEL DAG: ¿las exposiciones predicen la obesidad?")
    print("=" * 100)
    eslabon = verificar_supuesto_mediacion(d)
    dio.guardar_tabla(eslabon, "tabla_42_primer_eslabon_mediacion",
                      "Asociación de cada exposición con la obesidad")
    print(eslabon[["exposicion", "or_hacia_obesidad", "p", "veredicto"]].to_string(index=False))

    tabla, modelos = modelos_mediacion(d)
    dio.guardar_tabla(tabla, "tabla_43_efecto_total_vs_directo",
                      "Efecto total (modelo A) frente a efecto directo (modelo B)")
    dio.guardar_tabla(modelos["A"]["tabla_or"], "tabla_44_modelo_A_efecto_total",
                      "Modelo A: efecto total, sin obesidad en el ajuste")
    dio.guardar_tabla(modelos["B"]["tabla_or"], "tabla_45_modelo_B_efecto_directo",
                      "Modelo B: efecto directo, con obesidad en el ajuste")
    print("\n" + "=" * 100)
    print("EFECTO TOTAL FRENTE A EFECTO DIRECTO")
    print("=" * 100)
    print(tabla[["exposicion", "or_total_fmt", "or_directo_fmt", "cambio_pct",
                 "proporcion_mediada_pct", "lectura"]].to_string(index=False))

    # ── 2. Interacciones ──────────────────────────────────────────
    inter = interacciones_filtradas(d)
    dio.guardar_tabla(inter, "tabla_46_interacciones_filtradas",
                      "Interacciones evaluadas con los tres criterios")
    print("\n" + "=" * 100)
    print(f"INTERACCIONES · criterios: p(FDR) < 0,05 · razón de OR ≥ {RAZON_MINIMA} · "
          f"≥ {EVENTOS_MINIMOS} eventos por celda estrato × exposición")
    print("=" * 100)
    print(inter[["exposicion", "estratificador", "razon_or", "eventos_min_celda",
                 "p_homogeneidad", "p_fdr", "criterio_1_p_fdr", "criterio_2_magnitud",
                 "criterio_3_eventos", "sobrevive"]].head(18).to_string(index=False))
    print(f"\n  Evaluadas: {len(inter)}  |  Significativas sin filtro: "
          f"{int((inter.p_homogeneidad < 0.05).sum())}  |  "
          f"Sobreviven los tres criterios: {int(inter.sobrevive.sum())}")

    # ── 3. Imputación ─────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("IMPUTACIÓN MÚLTIPLE COMO SENSIBILIDAD")
    print("=" * 100)
    imp = imputacion_multiple(d)
    dio.guardar_tabla(imp, "tabla_47_imputacion_multiple",
                      "Casos completos frente a imputación múltiple (reglas de Rubin)")
    print(f"Faltantes en las variables del modelo: {imp.attrs['faltantes']}")
    print(f"Imputaciones: {imp.attrs['m']}\n")
    print(imp[["etiqueta", "or_casos_completos", "or_imputado", "cambio_pct",
               "fraccion_informacion_perdida", "conclusion_cambia"]].to_string(index=False))
    print(f"\n  Términos donde la conclusión cambia: {int(imp.conclusion_cambia.sum())} "
          f"de {len(imp)}")

    figura_mediacion(tabla)
    print("\nMediación, interacciones e imputación completadas.")


if __name__ == "__main__":
    main()
