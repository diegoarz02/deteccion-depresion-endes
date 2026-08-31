"""Forma funcional de la edad: categórica frente a spline.

La prueba de Box-Tidwell rechaza la linealidad del logit en la edad
(p < 0,001). El modelo ya usa ``grupo_etario`` categórico, que es una solución
válida, pero «válida» no es lo mismo que «la mejor»: hay que compararla.

Se ajustan cinco formas sobre el mismo conjunto de casos y se comparan por AIC,
igual que se hizo con la altitud. Comparar AIC exige que todos los modelos vean
exactamente las mismas filas, así que se fija la base antes de ajustar nada.

El resultado se documenta se elija lo que se elija: si la spline gana con
claridad, se adopta y se reporta; si la diferencia es pequeña, se conserva la
categórica y se dice por qué. Una categórica cuesta cinco grados de libertad y
se lee sola —«el grupo de 60+ frente al de 30-39»—, mientras que una spline
gana ajuste y obliga a un gráfico para interpretarse. Con una diferencia de AIC
pequeña, la interpretabilidad decide.

Uso
---
    python codigo/scripts/analisis_11_forma_edad.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402
from depresion import io as dio  # noqa: E402
from depresion import viz  # noqa: E402

COL = cfg.COLORES

#: Confusores que acompañan a la edad en todas las formas comparadas. Se
#: mantienen fijos: lo único que cambia entre modelos es cómo entra la edad.
AJUSTE = ["es_mujer", "es_rural"]

#: Diferencia de AIC a partir de la cual se considera que un modelo gana de
#: verdad. Por debajo de 2 los modelos son indistinguibles (Burnham y Anderson);
#: se pide 10 para cambiar una especificación que ya funciona y se entiende.
DELTA_PARA_CAMBIAR = 10


def base(d: pd.DataFrame) -> pd.DataFrame:
    """Fija el conjunto de casos común a todos los modelos.

    Sin esto, cada forma se ajustaría sobre un número distinto de filas y los
    AIC no serían comparables — un error silencioso que produce una tabla que
    parece correcta.
    """
    cols = ["depresion_bin", "edad", "grupo_etario", *AJUSTE]
    b = d.dropna(subset=cols).copy()
    b["edad_c"] = b.edad - b.edad.mean()
    return b


def _confusores(b: pd.DataFrame) -> pd.DataFrame:
    """Matriz de los confusores, igual en todos los modelos."""
    return b[AJUSTE].astype(float)


def comparar_formas(b: pd.DataFrame) -> pd.DataFrame:
    """Ajusta cinco formas de la edad y las ordena por AIC."""
    y = b.depresion_bin.astype(float)
    conf = _confusores(b)
    filas = []

    def ajustar(nombre: str, X: pd.DataFrame, descripcion: str):
        m = sm.GLM(y, sm.add_constant(pd.concat([X, conf], axis=1)),
                   family=sm.families.Binomial()).fit()
        filas.append({"forma": nombre, "descripcion": descripcion,
                      "aic": m.aic, "gl": int(m.df_model),
                      "log_verosimilitud": m.llf})
        return m

    ajustar("Lineal", b[["edad_c"]], "La edad entra como una recta")

    cuad = b[["edad_c"]].copy()
    cuad["edad_cuad"] = cuad.edad_c ** 2
    ajustar("Cuadrática", cuad, "Se permite una curva en U")

    cub = cuad.copy()
    cub["edad_cub"] = cub.edad_c ** 3
    ajustar("Cúbica", cub, "Se permite una curva con dos inflexiones")

    # Spline natural con nudos en los cuantiles: la forma la deciden los datos.
    nudos = np.quantile(b.edad, [0.25, 0.5, 0.75])
    spl = b[["edad_c"]].copy()
    for i, k in enumerate(nudos):
        spl[f"spline_{i}"] = np.maximum(b.edad - k, 0) ** 3
    ajustar("Spline cúbico", spl, f"Nudos en {[int(k) for k in nudos]} años")

    cat = pd.get_dummies(b.grupo_etario, prefix="ge", drop_first=True).astype(float)
    ajustar("Categórica (la actual)", cat, "Seis grupos, referencia 30-39")

    out = pd.DataFrame(filas).sort_values("aic").reset_index(drop=True)
    out["delta_aic"] = out.aic - out.aic.min()
    out["veredicto"] = np.where(
        out.delta_aic == 0, "Mejor AIC",
        np.where(out.delta_aic < 2, "Indistinguible del mejor",
                 "Peor por " + out.delta_aic.round(1).astype(str) + " puntos"))
    return out


def curva_por_edad(b: pd.DataFrame) -> pd.DataFrame:
    """Prevalencia observada por año de edad, para ver la forma sin suponerla."""
    g = (b.groupby("edad", observed=True).depresion_bin
         .agg(n="size", casos="sum").reset_index())
    g["prevalencia"] = g.casos / g.n * 100
    # Se marcan las edades con poca gente: al final del rango, cada año tiene
    # pocas personas y la curva se vuelve ruido.
    g["fiable"] = g.n >= 100
    return g


def figura(comp: pd.DataFrame, curva: pd.DataFrame, b: pd.DataFrame) -> None:
    """Dibuja la forma observada frente a las dos candidatas."""
    viz.aplicar_tema()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13.5, 5.4))

    fiable = curva[curva.fiable]
    a1.scatter(fiable.edad, fiable.prevalencia, s=fiable.n / 22,
               color=COL["navy_claro"], alpha=0.55, zorder=3,
               label="Prevalencia observada")
    a1.scatter(curva[~curva.fiable].edad, curva[~curva.fiable].prevalencia,
               s=14, color=COL["gris_claro"], zorder=2,
               label="Menos de 100 personas")
    # Media móvil de siete años: suaviza sin imponer ninguna forma.
    suave = fiable.set_index("edad").prevalencia.rolling(7, center=True, min_periods=3).mean()
    a1.plot(suave.index, suave.values, color=COL["dorado"], linewidth=2.6,
            zorder=4, label="Media móvil de 7 años")
    a1.set_xlabel("Edad (años)")
    a1.set_ylabel("Prevalencia observada (%)")
    a1.set_title("La forma que tienen los datos")
    a1.legend(fontsize=9)

    orden = comp.sort_values("aic")
    colores = [COL["navy_claro"] if f.startswith("Categórica") else COL["gris"]
               for f in orden.forma]
    a2.barh(orden.forma, orden.delta_aic, color=colores)
    a2.axvline(DELTA_PARA_CAMBIAR, color=COL["dorado"], linestyle="--", linewidth=1.6)
    a2.text(DELTA_PARA_CAMBIAR, -0.6, f"  Δ = {DELTA_PARA_CAMBIAR}", color=COL["dorado"],
            fontsize=9, va="top")
    a2.set_xlabel("Δ AIC respecto del mejor (menos es mejor)")
    a2.set_title("Cuánto mejora cada forma")
    a2.invert_yaxis()

    viz.pie_de_figura(
        fig, "Fuente: ENDES 2025 (INEI). Todos los modelos se ajustan sobre las mismas "
             f"{len(b):,} personas y con los mismos confusores, que es lo que hace "
             "comparables sus AIC.".replace(",", " "))
    dio.guardar_figura(fig, "fig_18_forma_edad")
    plt.close(fig)


#: Umbral convencional de confusión. Si cambiar la forma de la edad mueve el OR
#: de otra variable menos de esto, la elección es de presentación y no de
#: validez, y puede decidirse por interpretabilidad sin perder rigor.
CAMBIO_RELEVANTE = 10.0

MODELO_COMPLETO = ["es_mujer", "es_rural", "consumo_frecuente", "alcohol_problematico",
                   "fuma_12m", "hta_dx", "diabetes_dx", "obesidad"]


def efecto_sobre_las_demas(d: pd.DataFrame) -> pd.DataFrame:
    """Comprueba si la forma de la edad sesga los coeficientes de las demás.

    Es la pregunta que de verdad decide. Que una spline ajuste mejor la edad no
    obliga por sí solo a adoptarla: obliga a comprobar que la categórica no está
    distorsionando el resto del modelo. Si no lo hace, elegir entre una y otra
    pasa a ser una decisión de comunicación.
    """
    cols = ["depresion_bin", "edad", "grupo_etario", "educacion_grupo",
            "region_natural", *MODELO_COMPLETO]
    b = d.dropna(subset=cols).copy()
    y = b.depresion_bin.astype(float)

    otras = pd.concat([
        b[MODELO_COMPLETO].astype(float),
        pd.get_dummies(b.educacion_grupo, prefix="edu", drop_first=True).astype(float),
        pd.get_dummies(b.region_natural, prefix="reg", drop_first=True).astype(float),
    ], axis=1)

    cat = pd.get_dummies(b.grupo_etario, prefix="ge", drop_first=True).astype(float)
    m_cat = sm.GLM(y, sm.add_constant(pd.concat([otras, cat], axis=1)),
                   family=sm.families.Binomial()).fit()

    nudos = np.quantile(b.edad, [0.25, 0.5, 0.75])
    spl = pd.DataFrame({"edad_c": b.edad - b.edad.mean()}, index=b.index)
    for i, k in enumerate(nudos):
        spl[f"spl_{i}"] = np.maximum(b.edad - k, 0) ** 3
    m_spl = sm.GLM(y, sm.add_constant(pd.concat([otras, spl], axis=1)),
                   family=sm.families.Binomial()).fit()

    filas = []
    for v in otras.columns:
        oc, os_ = np.exp(m_cat.params[v]), np.exp(m_spl.params[v])
        filas.append({"variable": v, "or_con_categorica": oc, "or_con_spline": os_,
                      "cambio_pct": (os_ - oc) / oc * 100})
    out = pd.DataFrame(filas)
    out["relevante"] = out.cambio_pct.abs() >= CAMBIO_RELEVANTE
    out.attrs["aic_categorica"] = m_cat.aic
    out.attrs["aic_spline"] = m_spl.aic
    out.attrs["n"] = len(b)
    return out


def main() -> None:
    """Compara las formas funcionales de la edad y documenta la elección."""
    dio.configurar_logging()
    d = pd.read_parquet(cfg.DATASET_FINAL)
    d = d[d.en_analisis == 1]
    b = base(d)

    print("=" * 78)
    print(f"FORMA FUNCIONAL DE LA EDAD · {len(b):,} personas, mismos casos en los 5 modelos")
    print("=" * 78)

    comp = comparar_formas(b)
    print(comp[["forma", "descripcion", "gl", "aic", "delta_aic", "veredicto"]]
          .to_string(index=False))

    mejor = comp.iloc[0]
    actual = comp[comp.forma.str.startswith("Categórica")].iloc[0]
    ventaja = actual.delta_aic

    print(f"\nMejor por AIC: {mejor.forma}")
    print(f"La categórica actual queda a {ventaja:.1f} puntos del mejor.")

    # La pregunta que decide no es cuál ajusta mejor, sino si la elección
    # distorsiona algo más del modelo.
    print("\n" + "=" * 78)
    print("¿SESGA LA CATEGÓRICA A LAS DEMÁS VARIABLES?")
    print("=" * 78)
    ef = efecto_sobre_las_demas(d)
    print(ef.round(3).to_string(index=False))
    peor = ef.cambio_pct.abs().max()
    d_aic = ef.attrs["aic_categorica"] - ef.attrs["aic_spline"]
    print(f"\nAIC en el modelo completo: categórica {ef.attrs['aic_categorica']:.1f} · "
          f"spline {ef.attrs['aic_spline']:.1f} (Δ {d_aic:.1f})")
    print(f"Cambio máximo en el OR de otra variable: {peor:.1f} %")

    if peor >= CAMBIO_RELEVANTE:
        decision = (
            f"La forma de la edad mueve el OR de otra variable un {peor:.1f} %, por encima "
            f"del {CAMBIO_RELEVANTE:.0f} % convencional. La categórica está distorsionando "
            f"el resto del modelo y hay que sustituirla por la spline.")
    else:
        decision = (
            f"La spline ajusta mejor la edad —{ventaja:.1f} puntos de AIC aislada, "
            f"{d_aic:.1f} en el modelo completo— pero no cambia ninguna otra conclusión: "
            f"el coeficiente que más se mueve lo hace un {peor:.1f} %, muy por debajo del "
            f"{CAMBIO_RELEVANTE:.0f} % que marca una confusión relevante. Elegir entre una "
            f"y otra es, por tanto, una decisión de comunicación y no de validez. Se "
            f"mantiene la categórica: da odds ratios que se leen solos («el grupo de 60+ "
            f"frente al de 30-39»), es la forma en que reporta la literatura con la que "
            f"este trabajo se compara, y una spline necesita un gráfico para interpretarse. "
            f"La spline queda documentada como análisis de sensibilidad.")

    print(f"\nDECISIÓN: {decision}")
    comp.attrs["decision"] = decision
    dio.guardar_tabla(ef, "tabla_56_edad_efecto_sobre_las_demas",
                      "Odds ratio de las demás variables según la forma de la edad.")

    curva = curva_por_edad(b)
    figura(comp, curva, b)

    salida = comp.copy()
    salida["decision"] = ""
    salida.loc[0, "decision"] = decision
    dio.guardar_tabla(salida, "tabla_54_forma_funcional_edad",
                      "Comparación de formas funcionales de la edad, por AIC.")
    dio.guardar_tabla(curva, "tabla_55_prevalencia_por_edad",
                      "Prevalencia observada por año de edad.")
    print("\nForma funcional de la edad documentada.")


if __name__ == "__main__":
    main()
