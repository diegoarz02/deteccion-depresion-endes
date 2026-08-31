"""Regenera docs/diccionario_variables.md desde el dataset.

Existe porque el diccionario en Markdown se quedó congelado en la primera
corrida: decía «33 569 × 71» cuando el dataset ya tenía 82 columnas. Nada lo
regeneraba, así que la documentación y los datos podían divergir sin que
ninguna prueba lo notara. Ahora se deriva de ``tabla_00_diccionario.csv``, que
sí escribe ``construir_dataset.py``, y el bloque de agrupación es la única
parte que se mantiene a mano.

Uso
---
    python codigo/scripts/construir_dataset.py     # escribe la tabla 00
    python codigo/scripts/generar_diccionario.py   # la convierte a Markdown
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402

DESTINO = cfg.RAIZ / "docs" / "diccionario_variables.md"

#: Agrupación temática. El orden importa: una variable cae en el primer grupo
#: que la reclame, así que los grupos más específicos van antes.
GRUPOS: list[tuple[str, list[str]]] = [
    ("Desenlace", [
        "phq9_score", "phq9_completo", "depresion_bin", "depresion_leve_bin",
        "phq9_categoria", *[f"QS700{x}" for x in "ABCDEFGHI"]]),
    ("Diseño muestral", [
        "HHID", "QSNUMERO", "peso", "conglomerado", "estrato", "tiene_peso",
        "en_analisis"]),
    ("Geografía y territorio", [
        "ubigeo", "cod_departamento", "cod_provincia", "cod_distrito",
        "departamento", "departamento_norm", "NOMCCPP", "longitud", "latitud",
        "coord_estado", "area", "es_rural", "region_natural", "dominio_inei"]),
    ("Altitud", [
        "altitud", "altitud_categoria", "altitud_100m", "altitud_km",
        "gran_altitud"]),
    ("Confusor / sociodemográfica", [
        "edad", "edad_topeada", "grupo_etario", "sexo", "es_mujer",
        "educacion", "educacion_grupo"]),
    ("Exposición conductual", [
        "alcohol_alguna_vez", "consumo_alcohol_12m", "consumo_frecuente",
        "consumo_30d", "n_criterios_abuso", "alcohol_problematico",
        "n_criterios_dependencia", "alcohol_dependencia", "alcohol_categoria",
        "fuma_12m", "fuma_30d", "fuma_diario", "tabaco_categoria"]),
    ("Exposición social", [
        "estado_pareja", "tuvo_pareja", "violencia_fisica", "violencia_objeto",
        "violencia_max", "violencia_severidad"]),
    ("Exposición clínica", [
        "peso_kg", "talla_cm", "imc", "imc_categoria", "obesidad",
        "perimetro_abdominal", "obesidad_abdominal", "presion_sistolica",
        "presion_diastolica", "hta_medida", "hta_dx", "diabetes_dx",
        "n_cronicas", "tiene_cronica"]),
    ("Atención en salud", ["recibio_tratamiento_sm", "brecha_atencion"]),
]

CABECERA = ("| Variable | Tipo | N válido | % faltantes | Categorías o rango "
            "| Regla de construcción |\n|---|---|---:|---:|---|---|")


def _fila(r: pd.Series) -> str:
    """Compone una fila de la tabla, escapando lo que rompería el Markdown."""
    def limpio(v) -> str:
        return str("" if pd.isna(v) else v).replace("|", r"\|").replace("\n", " ")

    return (f"| `{r.variable}` | {limpio(r.tipo)} | {int(r.n_valido):,} "
            f"| {r.pct_faltantes} | {limpio(r.categorias)} "
            f"| {limpio(r.regla_de_construccion)} |")


def main() -> None:
    """Compone el Markdown y avisa si alguna variable quedó sin documentar."""
    d = pd.read_csv(cfg.RESULTADOS / "tablas" / "tabla_00_diccionario.csv")
    d.columns = [c.lstrip("﻿") for c in d.columns]
    n_filas = int(pd.read_parquet(cfg.DATASET_FINAL).shape[0])

    partes = [
        "# Diccionario de variables del dataset analítico",
        "",
        "Generado por `codigo/scripts/generar_diccionario.py` a partir de "
        "`resultados/tablas/tabla_00_diccionario.csv`.",
        f"Fuente: `datos/final/data.parquet` ({n_filas:,} × {len(d)}).".replace(",", " "),
        "",
        "La columna **regla de construcción** contiene la recodificación exacta "
        "aplicada; es la referencia para replicar el dataset en R o SPSS.",
        "",
        "> ⚠️ **No usar como predictores de `depresion_bin`:** "
        + ", ".join(f"`{v}`" for v in cfg.VARIABLES_CON_FUGA),
        "> — son fuga de información. Por eso no están en el dataset.",
        "",
    ]

    colocadas: set[str] = set()
    for titulo, nombres in GRUPOS:
        bloque = d[d.variable.isin(nombres)]
        if bloque.empty:
            continue
        # Se respeta el orden declarado en GRUPOS, no el del CSV.
        bloque = bloque.set_index("variable").reindex(
            [n for n in nombres if n in set(bloque.variable)]).reset_index()
        colocadas |= set(bloque.variable)
        partes += [f"## {titulo}", "", CABECERA]
        partes += [_fila(r) for _, r in bloque.iterrows()]
        partes.append("")

    huerfanas = d[~d.variable.isin(colocadas)]
    if not huerfanas.empty:
        partes += ["## Sin clasificar", "",
                   "Variables presentes en el dataset que no están asignadas a "
                   "ningún grupo de `GRUPOS`. Si aparece alguna aquí, hay que "
                   "clasificarla a mano en el script.", "", CABECERA]
        partes += [_fila(r) for _, r in huerfanas.iterrows()]
        partes.append("")

    sin_regla = d[d.regla_de_construccion.isna() | (d.regla_de_construccion == "")]

    DESTINO.write_text("\n".join(partes), encoding="utf-8")
    print(f"Escrito {DESTINO.relative_to(cfg.RAIZ)}: {len(d)} variables, "
          f"{len(GRUPOS)} grupos.")
    if not huerfanas.empty:
        print(f"ATENCIÓN: {len(huerfanas)} variables sin grupo: "
              f"{', '.join(huerfanas.variable)}")
    if not sin_regla.empty:
        print(f"ATENCIÓN: {len(sin_regla)} variables sin regla de construcción: "
              f"{', '.join(sin_regla.variable)}")


if __name__ == "__main__":
    main()
