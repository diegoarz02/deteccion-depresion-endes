"""Compara la réplica en R con las tablas de Python.

Que dos implementaciones independientes den el mismo número es la única prueba
real de que ninguna de las dos tiene un error de diseño muestral. ``survey`` de
R es la implementación de referencia del campo; ``svy`` en Python es la que usa
este proyecto. Si coinciden hasta el cuarto decimal, el diseño complejo está
bien declarado en ambas.

Lee los CSV que escribe la réplica —no su salida de consola: una tabla que R
parte en dos bloques por el ancho del terminal rompería cualquier parser.

Uso
---
    Rscript codigo/R/analisis_equivalente.R
    python codigo/scripts/verificar_equivalencia_R.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402
from depresion import io as dio  # noqa: E402

TABLAS = cfg.RESULTADOS / "tablas"

#: Diferencia máxima tolerada en un OR. Por encima de esto no es ruido
#: numérico de la optimización: es que una implementación hace algo distinto.
TOLERANCIA_OR = 0.01
TOLERANCIA_PCT = 0.05


def _exigir(ruta: Path) -> pd.DataFrame:
    if not ruta.exists():
        raise SystemExit(
            f"No existe {ruta.name}.\n"
            "Ejecuta primero: Rscript codigo/R/analisis_equivalente.R")
    return pd.read_csv(ruta)


def normalizar(termino: str) -> str:
    """Reduce un nombre de término a una forma común a R y a Python.

    R pega el nivel al nombre del factor (``grupo_etario60+``) y Python lo
    separa con un guion bajo (``grupo_etario_60+``). Como el propio nombre del
    factor ya lleva guiones bajos, no se puede quitar solo el separador: se
    eliminan todos, junto con espacios y mayúsculas, y ambas formas convergen.
    """
    return (termino.lower()
            .replace("[t.", "").replace("]", "")
            .replace("_", "").replace(" ", "").strip())


def comparar_or() -> pd.DataFrame:
    """Cruza los odds ratio de ambas implementaciones término a término."""
    py = pd.read_csv(TABLAS / "tabla_22_logistica_diseno_complejo.csv")
    r = _exigir(TABLAS / "tabla_R_logistica.csv")
    r = r[r.termino != "(Intercept)"]

    py["clave"] = py.termino.map(normalizar)
    r["clave"] = r.termino.map(normalizar)

    m = py.merge(r, on="clave", how="outer", suffixes=("_py", "_r"), indicator=True)
    m["diferencia"] = (m.or_py - m.or_r).abs()
    m["coincide"] = m.diferencia < TOLERANCIA_OR
    m["estado"] = m._merge.map({
        "both": "comparado", "left_only": "solo en Python", "right_only": "solo en R"})
    return (m[["clave", "or_py", "or_r", "diferencia", "coincide", "estado"]]
            .sort_values("diferencia", ascending=False, na_position="first"))


def comparar_diseno() -> pd.DataFrame:
    """Contrasta prevalencia, intervalo, efecto de diseño y muestra efectiva."""
    r = _exigir(TABLAS / "tabla_R_diseno.csv").set_index("cantidad").valor

    ctx = json.loads((cfg.RAIZ / "api" / "datos" / "contexto.json")
                     .read_text(encoding="utf-8"))["nacional"]
    deff = pd.read_csv(TABLAS / "tabla_51_deff_por_variable.csv")
    fila = deff[deff.variable == "depresion_bin"]
    if fila.empty:
        raise SystemExit("La tabla 51 no trae la fila de depresion_bin.")
    fila = fila.iloc[0]

    d = pd.read_parquet(cfg.DATASET_FINAL)
    analisis = d[d.en_analisis == 1].dropna(subset=["depresion_bin"])

    pares = [
        ("Prevalencia nacional (%)", ctx["prevalencia"], TOLERANCIA_PCT),
        ("IC inferior (%)", ctx["ic_inf"], TOLERANCIA_PCT),
        ("IC superior (%)", ctx["ic_sup"], TOLERANCIA_PCT),
        ("Efecto de diseño", float(fila.deff), TOLERANCIA_PCT),
        ("Tamaño de muestra efectivo", float(fila.n_efectivo), 5),
        ("Suma de ponderadores", float(analisis.peso.sum()), 1),
        ("Conglomerados", float(analisis.conglomerado.nunique()), 0),
        ("Población de análisis", float(len(analisis)), 0),
    ]
    out = pd.DataFrame([
        {"cantidad": c, "python": round(v, 4), "r": round(float(r.get(c, float("nan"))), 4),
         "tolerancia": t}
        for c, v, t in pares])
    out["diferencia"] = (out.python - out.r).abs()
    out["coincide"] = out.diferencia <= out.tolerancia
    return out


def main() -> None:
    """Ejecuta la comparación completa y guarda las tablas de equivalencia."""
    diseno = comparar_diseno()
    print("\nDISEÑO MUESTRAL · Python frente a R")
    print(diseno.to_string(index=False))

    ors = comparar_or()
    comparados = ors[ors.estado == "comparado"]
    print(f"\nODDS RATIO · {len(comparados)} de {len(ors)} términos comparados "
          f"(tolerancia {TOLERANCIA_OR})")
    print(ors.to_string(index=False))

    dio.guardar_tabla(diseno, "tabla_52_equivalencia_R_diseno")
    dio.guardar_tabla(ors, "tabla_53_equivalencia_R_or")

    huerfanos = (ors.estado != "comparado").sum()
    fallos = int((~diseno.coincide).sum() + (~comparados.coincide).sum())
    print(f"\nDiscrepancia máxima en los OR: {comparados.diferencia.max():.5f}")
    if huerfanos:
        print(f"ATENCIÓN: {huerfanos} términos existen en una sola implementación.")
    if fallos or huerfanos:
        raise SystemExit(1)
    print("Las dos implementaciones coinciden dentro de la tolerancia.")


if __name__ == "__main__":
    main()
