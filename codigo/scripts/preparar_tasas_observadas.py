"""Precalcula la tasa observada de tamizaje positivo por perfil.

Este script existe por el reencuadre de la aplicación. El número protagonista
deja de ser una predicción del modelo —que con un AUC de 0,667 y un valor
predictivo positivo de 0,147 no puede describir a una persona— y pasa a ser un
**hecho observado**: cuántas personas con un perfil parecido dieron positivo en
la ENDES 2025.

La diferencia no es cosmética. «El modelo estima que tienes un 19,9 % de
probabilidad» es una afirmación sobre quien consulta, y es una afirmación que
estos datos no sostienen. «De cada cien personas con tu perfil entrevistadas en
la ENDES, veinte dieron positivo» es una afirmación sobre la muestra, verificable
y correcta.

Descenso jerárquico
-------------------
Un perfil completo puede caer en una celda demasiado pequeña para estimar nada.
En vez de devolver ruido o no devolver nada, se busca la celda más específica
que cumpla los criterios de publicación y se declara **qué variables la
definen**, para que la interfaz pueda decir con precisión a qué se parece el
perfil.

Uso
---
    python codigo/scripts/preparar_tasas_observadas.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402
from depresion import encuesta as enc  # noqa: E402
from depresion import io as dio  # noqa: E402

DESTINO = cfg.RAIZ / "api" / "datos"

#: Niveles de agregación, del más específico al más general. La búsqueda baja
#: por esta escalera hasta encontrar una celda publicable.
NIVELES: list[list[str]] = [
    ["sexo", "grupo_etario", "educacion_grupo", "area", "region_natural"],
    ["sexo", "grupo_etario", "educacion_grupo", "area"],
    ["sexo", "grupo_etario", "educacion_grupo"],
    ["sexo", "grupo_etario"],
    ["sexo"],
]

#: Cómo describir cada nivel en la interfaz. El texto va después de
#: «personas del mismo…», así que se redacta para encajar en esa frase.
DESCRIPCION_NIVEL = {
    5: "sexo, grupo de edad, nivel educativo, área de residencia y región natural",
    4: "sexo, grupo de edad, nivel educativo y área de residencia",
    3: "sexo, grupo de edad y nivel educativo",
    2: "sexo y grupo de edad",
    1: "sexo",
}

#: Criterios para que una celda sirva. Lo que limita una proporción no es el
#: tamaño de la celda sino el **número de eventos**: con un desenlace del 7 %,
#: una celda de 120 personas puede tener 8 positivos, y sobre 8 positivos no se
#: estima nada. Exigir solo n dejaba celdas con 11 eventos de mediana en el
#: nivel más específico.
#:
#: El coeficiente de variación NO se usa aquí para excluir, sino para marcar.
#: Suprimir una celda imprecisa deja un hueco que el lector rellena solo, y casi
#: siempre mal; marcarla comunica el dato y su fragilidad a la vez. Además, con
#: CV como filtro casi todos los perfiles caían hasta «personas del mismo sexo»,
#: que es una comparación tan amplia que deja de informar.
N_MINIMO = 100
EVENTOS_MINIMOS = 20
CV_MAXIMO = cfg.CV_MAXIMO_PUBLICABLE


def _clave(valores) -> str:
    """Compone la clave de búsqueda que usará la aplicación."""
    return "|".join(str(v) for v in valores)


def tabla_de_un_nivel(diseno, columnas: list[str]) -> pd.DataFrame:
    """Estima la prevalencia observada para todas las celdas de un nivel."""
    t = enc.prevalencia(diseno, "depresion_bin", por=columnas, con_deff=False)
    t = t.rename(columns={"est": "prevalencia", "lci": "ic_inf", "uci": "ic_sup"})
    t["nivel"] = len(columnas)
    t["clave"] = [_clave(f) for f in t[columnas].to_numpy()]
    return t


def main() -> None:
    """Construye el catálogo de tasas observadas y lo escribe como JSON."""
    dio.configurar_logging()
    d = pd.read_parquet(cfg.DATASET_FINAL)
    d = d[d.en_analisis == 1].dropna(subset=["depresion_bin"])

    columnas_necesarias = sorted({c for n in NIVELES for c in n})
    diseno = enc.crear_diseno(d, columnas=[*columnas_necesarias, "depresion_bin"])

    # Los recuentos sin ponderar se calculan aparte: la interfaz muestra cuántas
    # personas reales hay detrás de la cifra, no la suma de sus ponderadores.
    catalogo: dict[str, dict] = {}
    for columnas in NIVELES:
        t = tabla_de_un_nivel(diseno, columnas)
        n_real = (d.dropna(subset=columnas).groupby(columnas, observed=True)
                  .depresion_bin.agg(n="size", eventos="sum").reset_index())
        n_real["eventos"] = n_real.eventos.astype(int)
        n_real["clave"] = [_clave(f) for f in n_real[columnas].to_numpy()]
        t = t.merge(n_real[["clave", "n", "eventos"]], on="clave", how="left")

        publicable = (t.n >= N_MINIMO) & (t.eventos >= EVENTOS_MINIMOS)
        for _, r in t[publicable].iterrows():
            # Las claves más específicas se escriben primero y no se pisan: si
            # un perfil tiene celda propia, esa manda sobre la general.
            catalogo.setdefault(r.clave, {
                "prevalencia": round(float(r.prevalencia), 2),
                "ic_inf": round(float(r.ic_inf), 2),
                "ic_sup": round(float(r.ic_sup), 2),
                "n": int(r.n),
                "eventos": int(r.eventos),
                # Cuatro decimales, no tres: con tres, una celda de CV 0,2004
                # se guarda como «0,2» y la marca de imprecisa parece un error
                # de quien la lee. El valor y la bandera tienen que concordar.
                "cv": round(float(r.cv), 4),
                "impreciso": bool(r.cv > CV_MAXIMO),
                "nivel": int(r.nivel),
                "definido_por": DESCRIPCION_NIVEL[int(r.nivel)],
            })
        imprecisas = int((publicable & (t.cv > CV_MAXIMO)).sum())
        print(f"  nivel {len(columnas)}: {len(t)} celdas, {int(publicable.sum())} utilizables "
              f"(n >= {N_MINIMO} y >= {EVENTOS_MINIMOS} eventos), {imprecisas} marcadas como imprecisas")

    salida = {
        "_fuente": "ENDES 2025 (INEI), módulo CSALUD01",
        "_criterio": (f"Solo se usan celdas con al menos {N_MINIMO} personas y "
                      f"{EVENTOS_MINIMOS} casos positivos. Las que superan un "
                      f"coeficiente de variación de {CV_MAXIMO} se marcan como "
                      f"imprecisas, no se suprimen."),
        "_orden_niveles": NIVELES,
        "tasas": catalogo,
    }
    DESTINO.mkdir(parents=True, exist_ok=True)
    ruta = DESTINO / "tasas_observadas.json"
    ruta.write_text(json.dumps(salida, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(catalogo)} celdas publicables -> {ruta.relative_to(cfg.RAIZ)} "
          f"({ruta.stat().st_size / 1024:.1f} kB)")


if __name__ == "__main__":
    main()
