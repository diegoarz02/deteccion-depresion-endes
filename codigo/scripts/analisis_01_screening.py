"""Fase 2 · Screening de variables candidatas (§8 del protocolo).

Evalúa cada variable candidata en seis dimensiones antes de modelar:
cobertura, varianza, celdas mínimas, asociación bivariada, multicolinealidad y
rol epidemiológico. Produce una decisión escrita y justificada por variable.

Principio: **no se excluye ninguna variable por tener p > 0,05.** Eso sería
p-hacking. Las exclusiones son metodológicas —fuga, causalidad reversa,
colinealidad, cobertura— y las inclusiones pueden ser teóricas aunque la señal
bivariada sea débil.

Uso
---
    python codigo/scripts/analisis_01_screening.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402
from depresion import epi  # noqa: E402
from depresion import io as dio  # noqa: E402

# ── Catálogo de candidatas ────────────────────────────────────────────
# rol: el papel causal propuesto ANTES de mirar los datos (ver DAG).
CANDIDATAS = [
    # (variable, etiqueta, bloque, rol propuesto)
    ("es_mujer", "Sexo femenino", "Sociodemográfica", "confusor"),
    ("grupo_etario", "Grupo etario", "Sociodemográfica", "confusor"),
    ("educacion_grupo", "Nivel educativo", "Sociodemográfica", "confusor"),
    ("es_rural", "Área rural", "Sociodemográfica", "confusor"),
    ("region_natural", "Región natural", "Sociodemográfica", "confusor"),

    ("consumo_alcohol_12m", "Consumo de alcohol (12 m)", "Conductual", "exposición"),
    ("consumo_frecuente", "Consumo frecuente de alcohol", "Conductual", "exposición"),
    ("alcohol_problematico", "Consumo problemático de alcohol", "Conductual", "exposición"),
    ("alcohol_dependencia", "Dependencia de alcohol", "Conductual", "exposición"),
    ("fuma_12m", "Fumó en 12 meses", "Conductual", "exposición"),
    ("fuma_diario", "Fuma a diario", "Conductual", "exposición"),

    ("violencia_fisica", "Violencia física de pareja", "Social", "exposición"),
    ("tuvo_pareja", "Tuvo pareja en 12 meses", "Social", "confusor"),

    ("hta_dx", "Hipertensión diagnosticada", "Clínica", "exposición"),
    ("hta_medida", "Hipertensión medida", "Clínica", "exposición"),
    ("diabetes_dx", "Diabetes diagnosticada", "Clínica", "exposición"),
    ("obesidad", "Obesidad (IMC ≥ 30)", "Clínica", "exposición"),
    ("obesidad_abdominal", "Obesidad abdominal", "Clínica", "exposición"),
    ("tiene_cronica", "Al menos una condición crónica", "Clínica", "exposición"),

    ("recibio_tratamiento_sm", "Recibió tratamiento en salud mental", "Atención", "consecuencia"),
]

# Exclusiones decididas antes de mirar los datos, por razones estructurales.
EXCLUSIONES_A_PRIORI = {
    "recibio_tratamiento_sm": (
        "CAUSALIDAD REVERSA. Recibir tratamiento por depresión es consecuencia "
        "del desenlace, no causa. Se analiza como brecha de atención, jamás "
        "como predictor."
    ),
    "tiene_cronica": (
        "REDUNDANTE. Es una combinación de hta_dx, diabetes_dx y obesidad, que "
        "ya entran por separado. Se conserva solo para el descriptivo."
    ),
    "hta_medida": (
        "SOLAPAMIENTO con hta_dx. Miden el mismo constructo por vías distintas "
        "(medición frente a autorreporte). Se conserva hta_dx, que además "
        "captura el contacto con el sistema de salud, y hta_medida pasa a "
        "análisis de sensibilidad."
    ),
    "obesidad_abdominal": (
        "SOLAPAMIENTO con obesidad. Se conserva el IMC por comparabilidad con "
        "la literatura; el perímetro abdominal queda para sensibilidad."
    ),
    "alcohol_dependencia": (
        "SUBCONJUNTO de alcohol_problematico con n muy pequeño. Se conserva "
        "alcohol_problematico y la dependencia pasa a sensibilidad."
    ),
    "fuma_diario": (
        "SUBCONJUNTO de fuma_12m. Se conserva fuma_12m por cobertura; el "
        "gradiente de intensidad se explora en sensibilidad."
    ),
    "consumo_alcohol_12m": (
        "SOLAPAMIENTO con consumo_frecuente, que capta la dosis y es la "
        "hipótesis de interés. Se conserva consumo_frecuente."
    ),
}


def evaluar(df: pd.DataFrame, var: str, etiqueta: str, bloque: str, rol: str) -> dict:
    """Aplica las seis comprobaciones del protocolo a una variable."""
    s = df[var]
    fila = {"variable": var, "etiqueta": etiqueta, "bloque": bloque, "rol_propuesto": rol}

    # 1. Cobertura
    fila["cobertura_pct"] = round(s.notna().mean() * 100, 2)
    fila["n_valido"] = int(s.notna().sum())

    # 2. Varianza (concentración de la categoría modal)
    vc = s.value_counts(normalize=True, dropna=True)
    fila["pct_modal"] = round(vc.iloc[0] * 100, 2) if len(vc) else np.nan
    fila["n_categorias"] = int(s.nunique())

    # 3 y 4. Celdas mínimas y asociación bivariada
    binaria = set(s.dropna().unique()) <= {0, 1}
    if binaria and s.nunique() == 2:
        r = epi.odds_ratio(s, df.depresion_bin)
        rp = epi.razon_prevalencias(s, df.depresion_bin)
        fila.update({
            "celda_minima": r["celda_minima"], "or_crudo": r["or"],
            "or_ic_inf": r["ic_inf"], "or_ic_sup": r["ic_sup"], "p": r["p"],
            "rp_cruda": rp["rp"], "advertencia": r["advertencia"],
        })
    else:
        # Categórica de más de dos niveles: chi-cuadrado global
        from scipy import stats
        d = df[[var, "depresion_bin"]].dropna()
        t = pd.crosstab(d[var].astype(str), d.depresion_bin)
        fila["celda_minima"] = int(t.values.min()) if t.size else 0
        fila["p"] = stats.chi2_contingency(t)[1] if t.shape[0] > 1 else np.nan
        fila["or_crudo"] = np.nan
        fila["advertencia"] = "Categórica politómica: OR por categoría en el modelo"
    return fila


def main() -> None:
    """Ejecuta el screening y guarda la tabla de decisiones."""
    dio.configurar_logging()
    df = pd.read_parquet(cfg.DATASET_FINAL)
    base = df[df.en_analisis == 1].dropna(subset=["depresion_bin"]).copy()
    print(f"Población de análisis: {len(base):,}")

    filas = [evaluar(base, v, e, b, r) for v, e, b, r in CANDIDATAS
             if v in base.columns]
    tabla = pd.DataFrame(filas)

    # 5. Multicolinealidad entre las exposiciones binarias que sobreviven
    binarias = [v for v, _, _, r in CANDIDATAS
                if v in base.columns and r == "exposición"
                and set(base[v].dropna().unique()) <= {0.0, 1.0}]
    pares = []
    for i, a in enumerate(binarias):
        for b in binarias[i + 1:]:
            v = epi.cramers_v(base[a], base[b])
            if v > 0.3:
                pares.append({"var_a": a, "var_b": b, "cramers_v": round(v, 3)})
    colin = pd.DataFrame(pares).sort_values("cramers_v", ascending=False) if pares else pd.DataFrame()

    # 6. Decisión razonada
    decisiones, justificaciones = [], []
    for _, r in tabla.iterrows():
        v = r.variable
        if v in EXCLUSIONES_A_PRIORI:
            decisiones.append("sensibilidad" if "sensibilidad" in EXCLUSIONES_A_PRIORI[v] else "excluir")
            justificaciones.append(EXCLUSIONES_A_PRIORI[v])
        elif r.cobertura_pct < 60 and v != "violencia_fisica":
            decisiones.append("excluir")
            justificaciones.append(f"Cobertura {r.cobertura_pct} % sin justificación estructural.")
        elif v == "violencia_fisica":
            decisiones.append("incluir (subpoblación)")
            justificaciones.append(
                "Cobertura del 65,3 % por salto estructural: solo se pregunta a quien tuvo "
                "pareja. No es no-respuesta. Se analiza como SUBPOBLACIÓN (n = 19 841), "
                "marcándola sobre el objeto de diseño, no filtrando los datos."
            )
        elif (pd.notna(r.get("pct_modal")) and r.pct_modal > 98
              and pd.notna(r.get("celda_minima")) and r.celda_minima < 10):
            decisiones.append("excluir")
            justificaciones.append(
                f"Varianza casi nula ({r.pct_modal} % en una categoría) Y celda mínima "
                f"n={int(r.celda_minima)}: no es estimable."
            )
        elif pd.notna(r.get("celda_minima")) and r.celda_minima < 10:
            decisiones.append("excluir")
            justificaciones.append(f"Celda mínima n={int(r.celda_minima)} (<10): estimador inestable.")
        else:
            decisiones.append("incluir")
            justificaciones.append(
                "Cobertura adecuada, varianza suficiente y celdas con n ≥ 10. "
                + ("Confusor por criterio de puerta trasera del DAG."
                   if r.rol_propuesto == "confusor"
                   else "Exposición de interés según el marco conceptual.")
            )
    tabla["DECISION"] = decisiones
    tabla["JUSTIFICACION"] = justificaciones

    # p ajustado por comparaciones múltiples, como sensibilidad
    tabla["p_fdr"] = epi.ajustar_p(tabla.p, "fdr_bh")
    tabla["p_bonferroni"] = epi.ajustar_p(tabla.p, "bonferroni")

    orden = ["variable", "etiqueta", "bloque", "rol_propuesto", "n_valido",
             "cobertura_pct", "pct_modal", "n_categorias", "celda_minima",
             "or_crudo", "or_ic_inf", "or_ic_sup", "rp_cruda", "p", "p_fdr",
             "p_bonferroni", "advertencia", "DECISION", "JUSTIFICACION"]
    tabla = tabla[[c for c in orden if c in tabla.columns]]

    dio.guardar_tabla(tabla, "tabla_05_screening_variables",
                      "Screening de variables candidatas con decisión justificada")
    if len(colin):
        dio.guardar_tabla(colin, "tabla_05b_colinealidad",
                          "Pares de exposiciones con V de Cramér > 0,30")

    incluidas = tabla[tabla.DECISION.str.startswith("incluir")]

    # El GVIF se calcula sobre el modelo principal, SIN las variables definidas
    # solo en la subpoblación con pareja: al descartar filas por lista,
    # `tuvo_pareja` quedaría constante y su GVIF sería un artefacto, no
    # colinealidad real. La subpoblación se evalúa aparte.
    subpoblacion = {"violencia_fisica", "tuvo_pareja"}
    vif_vars = [v for v in incluidas.variable if v in base.columns and v not in subpoblacion]
    vif = epi.vif(base, vif_vars)
    dio.guardar_tabla(vif, "tabla_05c_gvif",
                      "GVIF del modelo principal (Fox y Monette, por bloque de factor)")

    con_pareja = base[base.tuvo_pareja == 1]
    vif_sub = epi.vif(con_pareja, [*vif_vars, "violencia_fisica"])
    dio.guardar_tabla(vif_sub, "tabla_05d_gvif_subpoblacion",
                      "GVIF en la subpoblación con pareja, incluyendo violencia física")

    print("\n" + "=" * 100)
    print("SCREENING DE VARIABLES")
    print("=" * 100)
    with pd.option_context("display.width", 250, "display.max_colwidth", 46):
        print(tabla[["variable", "cobertura_pct", "pct_modal", "celda_minima",
                     "or_crudo", "p", "DECISION"]].to_string(index=False))
    print(f"\nIncluidas: {len(incluidas)}  |  Excluidas: {(tabla.DECISION == 'excluir').sum()}"
          f"  |  Sensibilidad: {(tabla.DECISION == 'sensibilidad').sum()}")
    print(f"\nGVIF comparable máximo (modelo principal): {vif.gvif_comparable.max():.2f}")
    print(f"GVIF comparable máximo (subpoblación con pareja): {vif_sub.gvif_comparable.max():.2f}")
    print("  (referencia: 2,24 equivale a VIF 5; 3,16 equivale a VIF 10)")
    if len(colin):
        print(f"\nPares colineales (V > 0,30):\n{colin.to_string(index=False)}")


if __name__ == "__main__":
    main()
