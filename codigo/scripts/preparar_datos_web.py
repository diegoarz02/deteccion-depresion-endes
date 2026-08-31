"""Precalcula los datos que sirve la aplicación web.

La API de producción corre con ~512 MB de RAM y un requirements mínimo: sin
pandas, sin geopandas, sin shap. Todo lo que la web necesita mostrar se calcula
aquí, en local, y se deja escrito como JSON estático.

Uso
---
    python codigo/scripts/preparar_datos_web.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402

DESTINO = cfg.RAIZ / "api" / "datos"


def main() -> None:
    """Escribe el contexto departamental y el GeoJSON ligero para la web."""
    DESTINO.mkdir(parents=True, exist_ok=True)

    dep = pd.read_csv(cfg.TABLAS / "tabla_48_prevalencia_departamental_geo.csv")
    brecha = pd.read_csv(cfg.TABLAS / "tabla_50_brecha_departamental.csv")
    brecha["cod_departamento"] = brecha.cod_departamento.astype(str).str.zfill(2)
    dep["cod_departamento"] = dep.cod_departamento.astype(str).str.zfill(2)
    dep = dep.merge(brecha[["cod_departamento", "brecha"]], on="cod_departamento", how="left")

    alt = pd.read_parquet(cfg.DATASET_FINAL)
    alt = alt[alt.en_analisis == 1]
    altitud = alt.groupby("cod_departamento").altitud.mean().round(0)

    departamentos = []
    for _, r in dep.sort_values("departamento").iterrows():
        departamentos.append({
            "codigo": r.cod_departamento,
            "nombre": r.departamento,
            "prevalencia": round(float(r.prevalencia), 2),
            "ic_inf": round(float(r.ic_inf), 2),
            "ic_sup": round(float(r.ic_sup), 2),
            "n": int(r.n),
            "brecha": round(float(r.brecha), 1) if pd.notna(r.brecha) else None,
            "altitud_media": int(altitud.get(r.cod_departamento, 0)),
        })

    nacional = pd.read_csv(cfg.TABLAS / "tabla_08_prevalencias_ponderadas.csv")
    total = nacional[nacional.variable == "Total"].iloc[0]

    contexto = {
        "nacional": {
            "prevalencia": round(float(total.prevalencia), 2),
            "ic_inf": round(float(total.ic_inf), 2),
            "ic_sup": round(float(total.ic_sup), 2),
            "n": int(total.n),
            "brecha": round(float(pd.read_csv(cfg.TABLAS / "tabla_11_brecha_atencion.csv")
                                  .brecha.iloc[0]), 1),
        },
        "departamentos": departamentos,
        "subgrupos": [
            {"variable": r.variable, "categoria": r.categoria,
             "prevalencia": round(float(r.prevalencia), 2), "n": int(r.n)}
            for _, r in nacional[nacional.variable != "Total"].iterrows()
        ],
        "fuente": "ENDES 2025 (INEI)",
    }
    (DESTINO / "contexto.json").write_text(
        json.dumps(contexto, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # GeoJSON simplificado: el navegador no debe descargar megabytes de fronteras
    origen = cfg.GEOJSON_WEB / "departamentos.geojson"
    if origen.exists():
        geo = json.loads(origen.read_text(encoding="utf-8"))
        for f in geo["features"]:
            props = f["properties"]
            f["properties"] = {
                "codigo": str(props.get("cod_departamento", "")).zfill(2),
                "nombre": props.get("departamento") or props.get("DEPARTAMEN", ""),
                "prevalencia": props.get("prevalencia"),
            }
        salida = DESTINO / "departamentos.geojson"
        salida.write_text(json.dumps(geo, ensure_ascii=False, separators=(",", ":")),
                          encoding="utf-8")
        print(f"  departamentos.geojson  {salida.stat().st_size / 1024:.0f} KB")

    coef = cfg.MODELOS / "coeficientes_logistico.json"
    if coef.exists():
        (DESTINO / "coeficientes.json").write_text(coef.read_text(encoding="utf-8"),
                                                   encoding="utf-8")

    tam = (DESTINO / "contexto.json").stat().st_size / 1024
    print(f"  contexto.json          {tam:.0f} KB · {len(departamentos)} departamentos")
    print(f"\nDatos de la web escritos en {DESTINO}")


if __name__ == "__main__":
    main()
