"""Efecto de diseño por variable (§12.4 de la segunda corrida).

El `deff` dice cuánta información real aporta la muestra frente a un muestreo
aleatorio simple del mismo tamaño. Un deff de 3 significa que 30 000 encuestas
informan como 10 000 tomadas al azar.

Importa reportarlo **por variable**, no solo el global: las variables que se
agrupan geográficamente —altitud, área, región— tienen mucho más agrupamiento
que las que se distribuyen de forma pareja dentro de cada conglomerado, como el
sexo. Un deff de 1 en el sexo y de 12 en la región cuentan cosas distintas
sobre la misma muestra.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402
from depresion import encuesta as enc  # noqa: E402
from depresion import io as dio  # noqa: E402

VARIABLES = [
    ("depresion_bin", "Depresión (PHQ-9 ≥ 10)", "proporcion"),
    ("depresion_leve_bin", "Síntomas leves o más (PHQ-9 ≥ 5)", "proporcion"),
    ("es_mujer", "Sexo femenino", "proporcion"),
    ("es_rural", "Residencia rural", "proporcion"),
    ("consumo_frecuente", "Consumo frecuente de alcohol", "proporcion"),
    ("alcohol_problematico", "Consumo problemático de alcohol", "proporcion"),
    ("fuma_12m", "Tabaquismo en 12 meses", "proporcion"),
    ("hta_dx", "Hipertensión diagnosticada", "proporcion"),
    ("diabetes_dx", "Diabetes diagnosticada", "proporcion"),
    ("obesidad", "Obesidad", "proporcion"),
    ("violencia_fisica", "Violencia física de pareja", "proporcion"),
    ("phq9_score", "Puntaje PHQ-9", "media"),
    ("edad", "Edad", "media"),
    ("imc", "Índice de masa corporal", "media"),
    ("altitud", "Altitud de residencia", "media"),
]


def main() -> None:
    """Calcula el deff de cada variable y su tamaño de muestra efectivo."""
    dio.configurar_logging()
    df = pd.read_parquet(cfg.DATASET_FINAL)
    base = df[df.en_analisis == 1].copy()

    filas = []
    for var, etiqueta, tipo in VARIABLES:
        if var not in base.columns:
            continue
        d = base.dropna(subset=[var])
        if len(d) < 100:
            continue
        diseno = enc.crear_diseno(d, [var])
        try:
            r = (enc.prevalencia(diseno, var) if tipo == "proporcion"
                 else enc.media(diseno, var))
            deff = float(r["deff"].iloc[0])
            filas.append({
                "variable": var, "etiqueta": etiqueta, "tipo": tipo,
                "n": len(d), "deff": deff,
                "n_efectivo": enc.tamano_efectivo(len(d), deff),
                "pct_informacion_conservada": 100 / deff,
            })
        except Exception as e:
            filas.append({"variable": var, "etiqueta": etiqueta, "tipo": tipo,
                          "n": len(d), "deff": float("nan"), "n_efectivo": float("nan"),
                          "pct_informacion_conservada": float("nan"),
                          "nota": str(e)[:70]})

    out = pd.DataFrame(filas).sort_values("deff", ascending=False)
    out["lectura"] = out.deff.map(
        lambda d: "Agrupamiento fuerte: la variable se concentra por conglomerado"
        if d >= 4 else ("Agrupamiento moderado" if d >= 2
                        else "Se distribuye de forma pareja dentro de los conglomerados"))
    dio.guardar_tabla(out, "tabla_51_deff_por_variable",
                      "Efecto de diseño y tamaño de muestra efectivo por variable")

    print("=" * 104)
    print("EFECTO DE DISEÑO POR VARIABLE")
    print("=" * 104)
    print(out[["etiqueta", "tipo", "n", "deff", "n_efectivo",
               "pct_informacion_conservada", "lectura"]].to_string(index=False))
    print(f"\n  Mediana del deff: {out.deff.median():.2f}")
    print(f"  Rango: {out.deff.min():.2f} – {out.deff.max():.2f}")
    print("\n  Un deff de 3 significa que la muestra informa como una aleatoria simple")
    print("  tres veces menor. Calcular un tamaño de muestra sin él lo deja corto.")


if __name__ == "__main__":
    main()
