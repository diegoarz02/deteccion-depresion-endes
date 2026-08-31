"""Fase 2 · Modelos predictivos e interpretabilidad (§11.5 del protocolo).

Extra de portafolio, **claramente separado del análisis inferencial**: aquí la
pregunta es "¿se puede ordenar el riesgo?", no "¿cuál es el efecto de X?".

Dos decisiones que separan esto de un tutorial:

1. **Partición por conglomerado.** Dos personas del mismo conglomerado se
   parecen entre sí; repartirlas entre entrenamiento y prueba es fuga. Se usa
   ``StratifiedGroupKFold`` agrupando por ``conglomerado``.
2. **Sin ponderar, y dicho explícitamente.** Los pesos corrigen el diseño para
   estimar parámetros poblacionales; aquí el objetivo es ordenar individuos.
   Son cosas distintas y no se sustituyen.

Uso
---
    python codigo/scripts/analisis_06_ml.py
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402
from depresion import io as dio  # noqa: E402
from depresion import modelos as mod  # noqa: E402
from depresion import viz  # noqa: E402

warnings.filterwarnings("ignore", category=UserWarning)
COL = cfg.COLORES

PREDICTORES = ["es_mujer", "grupo_etario", "educacion_grupo", "es_rural", "region_natural",
               "consumo_frecuente", "alcohol_problematico", "fuma_12m",
               "hta_dx", "diabetes_dx", "obesidad", "imc", "edad"]

REFERENCIAS = {"grupo_etario": "30-39", "educacion_grupo": "Superior", "region_natural": "Costa"}


def preparar(df: pd.DataFrame):
    """Construye X, y y los grupos de conglomerado para la validación."""
    d = df.dropna(subset=["depresion_bin", *PREDICTORES, "conglomerado"]).copy()
    X, etiquetas = mod.matriz_diseno(d, PREDICTORES, REFERENCIAS)
    return X, d.depresion_bin.astype(int).values, d.conglomerado.values, etiquetas


def construir_modelos(razon_desbalance: float) -> dict:
    """Define los modelos a comparar, todos con corrección de desbalance."""
    from lightgbm import LGBMClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from xgboost import XGBClassifier

    s = cfg.RANDOM_SEED
    return {
        "Logística regularizada": Pipeline([
            ("escala", StandardScaler()),
            ("clf", LogisticRegression(penalty="l2", C=1.0, max_iter=2000,
                                       class_weight="balanced", random_state=s)),
        ]),
        "Random Forest": RandomForestClassifier(
            n_estimators=250, max_depth=8, min_samples_leaf=25,
            class_weight="balanced_subsample", random_state=s, n_jobs=4),
        "XGBoost": XGBClassifier(
            n_estimators=350, max_depth=4, learning_rate=0.05,
            subsample=0.85, colsample_bytree=0.85, reg_lambda=2.0,
            scale_pos_weight=razon_desbalance, eval_metric="aucpr",
            random_state=s, n_jobs=4, tree_method="hist"),
        "LightGBM": LGBMClassifier(
            n_estimators=350, max_depth=5, learning_rate=0.05, num_leaves=24,
            subsample=0.85, colsample_bytree=0.85, reg_lambda=2.0,
            scale_pos_weight=razon_desbalance, random_state=s, n_jobs=4, verbose=-1),
    }


def validar(modelos: dict, X, y, grupos, n_splits: int = 5) -> tuple[pd.DataFrame, dict]:
    """Validación cruzada estratificada y agrupada por conglomerado."""
    from sklearn.model_selection import StratifiedGroupKFold

    cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=cfg.RANDOM_SEED)
    particiones = list(cv.split(X, y, groups=grupos))

    filas, predicciones = [], {}
    for nombre, m in modelos.items():
        p_oof = np.zeros(len(y))
        for tr, te in particiones:
            mm = __import__("copy").deepcopy(m)
            mm.fit(X.iloc[tr], y[tr])
            p_oof[te] = mm.predict_proba(X.iloc[te])[:, 1]
        predicciones[nombre] = p_oof
        met = mod.metricas_clasificacion(y, p_oof)
        filas.append({"modelo": nombre, **{k: v for k, v in met.items()
                                           if k not in ("vp", "vn", "fp", "fn")}})
        print(f"  {nombre:26s} AUC-ROC={met['auc_roc']:.4f}  AUC-PR={met['auc_pr']:.4f}  "
              f"sens={met['sensibilidad']:.3f}  espec={met['especificidad']:.3f}  F1={met['f1']:.3f}")

    # Referencia obligada: el modelo trivial
    filas.append({"modelo": "Modelo trivial (predice 'nadie')", "umbral": np.nan,
                  "auc_roc": 0.5, "auc_pr": float(y.mean()), "prevalencia": float(y.mean()),
                  "sensibilidad": 0.0, "especificidad": 1.0, "vpp": np.nan, "vpn": 1 - y.mean(),
                  "f1": 0.0, "exactitud": 1 - float(y.mean()),
                  "exactitud_modelo_trivial": 1 - float(y.mean())})
    return pd.DataFrame(filas), predicciones


def figura_comparacion(y, predicciones: dict, resultados: pd.DataFrame) -> None:
    """Curvas ROC y precisión-exhaustividad de todos los modelos."""
    from sklearn.metrics import precision_recall_curve, roc_curve

    viz.aplicar_tema()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13.5, 5.8))
    for (nombre, p), color in zip(predicciones.items(), cfg.PALETA_CATEGORICA, strict=False):
        fpr, tpr, _ = roc_curve(y, p)
        auc = resultados.loc[resultados.modelo == nombre, "auc_roc"].iloc[0]
        a1.plot(fpr, tpr, color=color, linewidth=2, label=f"{nombre} ({auc:.3f})")
        prec, rec, _ = precision_recall_curve(y, p)
        aupr = resultados.loc[resultados.modelo == nombre, "auc_pr"].iloc[0]
        a2.plot(rec, prec, color=color, linewidth=2, label=f"{nombre} ({aupr:.3f})")
    a1.plot([0, 1], [0, 1], "--", color=COL["gris"], linewidth=1.2)
    a1.set_xlabel("1 − especificidad")
    a1.set_ylabel("Sensibilidad")
    a1.set_title("Curvas ROC")
    a1.legend(loc="lower right", fontsize=9)
    a2.axhline(y.mean(), color=COL["gris"], linestyle="--", linewidth=1.2,
               label=f"Azar ({y.mean():.3f})")
    a2.set_xlabel("Exhaustividad (sensibilidad)")
    a2.set_ylabel("Precisión (VPP)")
    a2.set_title("Curvas precisión-exhaustividad")
    a2.legend(loc="upper right", fontsize=9)
    fig.suptitle("Comparación de modelos predictivos — validación agrupada por conglomerado",
                 fontsize=14, fontweight="bold", color=COL["navy"], y=1.02)
    viz.pie_de_figura(
        fig, "Fuente: ENDES 2025 (INEI). Con 6 % de eventos, la curva PR es más informativa "
             "que la ROC.")
    dio.guardar_figura(fig, "fig_13_comparacion_modelos_ml")
    plt.close(fig)


def analisis_shap(modelo, X, etiquetas: dict) -> tuple[pd.DataFrame, np.ndarray]:
    """Calcula los valores SHAP y su importancia global."""
    import shap

    expl = shap.TreeExplainer(modelo)
    muestra = X.sample(min(2500, len(X)), random_state=cfg.RANDOM_SEED)
    valores = expl.shap_values(muestra)
    # Según la versión de shap y el modelo, la salida binaria llega como lista de
    # dos matrices o como un array 3D (casos, variables, clases). En ambos casos
    # interesa la clase positiva.
    if isinstance(valores, list):
        valores = valores[1]
    valores = np.asarray(valores)
    if valores.ndim == 3:
        valores = valores[:, :, 1]
    imp = pd.DataFrame({
        "variable": X.columns,
        "etiqueta": [etiquetas.get(c, c) for c in X.columns],
        "shap_medio_abs": np.abs(valores).mean(axis=0),
    }).sort_values("shap_medio_abs", ascending=False)
    imp["importancia_relativa"] = imp.shap_medio_abs / imp.shap_medio_abs.sum() * 100
    return imp, valores, muestra


def figura_shap(imp: pd.DataFrame, valores, muestra) -> None:
    """Importancia global SHAP y comparación con los OR del modelo epidemiológico."""
    viz.aplicar_tema()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14.5, 6.6))

    d = imp.head(14).iloc[::-1]
    a1.barh(np.arange(len(d)), d.shap_medio_abs, color=COL["navy"], height=0.7)
    a1.set_yticks(np.arange(len(d)))
    a1.set_yticklabels(d.etiqueta, fontsize=9)
    a1.set_xlabel("|SHAP| medio")
    a1.set_title("Importancia global (SHAP)")

    # Diagrama de dispersión SHAP para la variable más importante
    top = imp.variable.iloc[0]
    j = list(muestra.columns).index(top)
    a2.scatter(muestra[top], valores[:, j], s=7, alpha=0.3, color=COL["dorado"])
    a2.axhline(0, color=COL["gris"], linewidth=1)
    a2.set_xlabel(imp.etiqueta.iloc[0])
    a2.set_ylabel("Valor SHAP (log-odds)")
    a2.set_title(f"Dependencia SHAP · {imp.etiqueta.iloc[0]}")

    fig.suptitle("Interpretabilidad del modelo predictivo", fontsize=14,
                 fontweight="bold", color=COL["navy"], y=1.0)
    fig.tight_layout()
    viz.pie_de_figura(fig)
    dio.guardar_figura(fig, "fig_14_shap")
    plt.close(fig)


def comparar_shap_con_or(imp: pd.DataFrame) -> pd.DataFrame:
    """Contrasta el ranking de SHAP con el de los OR ajustados.

    La pregunta interesante no es cuál gana, sino si el modelo aprende lo mismo
    que dice la epidemiología. Coincidir refuerza ambos resultados; discrepar
    señala dónde mirar.
    """
    ruta = cfg.TABLAS / "tabla_22_logistica_diseno_complejo.csv"
    if not ruta.exists():
        return pd.DataFrame()
    orr = pd.read_csv(ruta)
    orr["magnitud_or"] = (np.log(orr["or"])).abs()
    orr = orr.sort_values("magnitud_or", ascending=False).reset_index(drop=True)
    orr["rango_or"] = orr.index + 1

    s = imp.copy().reset_index(drop=True)
    s["rango_shap"] = s.index + 1
    s["clave"] = s.variable.str.replace("__", "_", regex=False)

    m = s.merge(orr[["termino", "or", "p", "rango_or", "magnitud_or"]],
                left_on="clave", right_on="termino", how="inner")
    m["diferencia_rango"] = m.rango_shap - m.rango_or
    return m[["etiqueta", "rango_shap", "rango_or", "diferencia_rango",
              "shap_medio_abs", "or", "p"]].sort_values("rango_shap")


def escribir_model_card(resultados: pd.DataFrame, imp: pd.DataFrame, n: int, prev: float) -> None:
    """Genera la ficha del modelo con sus usos previstos y prohibidos."""
    mejor = resultados.iloc[resultados.auc_pr.idxmax()]
    texto = f"""# Ficha del modelo — Tamizaje de riesgo de depresión (ENDES 2025)

## Uso previsto

Instrumento de **tamizaje epidemiológico poblacional** con fines académicos y de
salud pública. Estima la probabilidad de que una persona presente sintomatología
depresiva moderada o grave (PHQ-9 ≥ 10) a partir de características
sociodemográficas, conductuales y clínicas.

> {cfg.DISCLAIMER}

## Población

Personas de 15 años a más residentes en el Perú, según la ENDES 2025 del INEI.
Muestra de entrenamiento: {n:,} personas, prevalencia del desenlace {prev:.2%}.

## Datos y variables

Predictores: sexo, grupo etario, nivel educativo, área de residencia, región
natural, consumo frecuente y problemático de alcohol, tabaquismo, hipertensión
y diabetes diagnosticadas, obesidad, IMC y edad.

**Excluidas deliberadamente** por fuga de información: `QS702` (dificultad
funcional), `QS703` y `QS704A–I` (segunda batería PHQ-9 de 12 meses). Su
cobertura está determinada por el propio desenlace.

**Excluida por causalidad reversa:** haber recibido tratamiento en salud mental.

## Validación

Validación cruzada de 5 particiones, **estratificada y agrupada por conglomerado
muestral**. Agrupar importa: dos personas del mismo conglomerado se parecen
entre sí, y repartirlas entre entrenamiento y prueba inflaría el rendimiento.

El modelo se entrena **sin ponderadores**. Los pesos de ENDES corrigen el diseño
para estimar parámetros poblacionales; aquí el objetivo es ordenar individuos.
No son intercambiables.

**Verificación cruzada con R.** Las estimaciones con diseño complejo se
replicaron con el paquete `survey` de R, que es la implementación de referencia
del campo (`codigo/R/analisis_equivalente.R`). Los 17 términos del modelo
logístico coinciden con una discrepancia máxima de 0,0005 en el odds ratio, y
también coinciden la prevalencia, su intervalo, el efecto de diseño (3,09) y el
tamaño de muestra efectivo (9 774). Que dos implementaciones independientes
lleguen al mismo número es la única prueba real de que el diseño muestral está
bien declarado.

**Efecto de diseño.** Con deff ≈ 3,1, las 30 226 entrevistas aportan tanta
información como unas 9 774 tomadas al azar. Un análisis que ignorase el
conglomerado daría intervalos casi la mitad de anchos de lo que corresponde.

## Métricas

{resultados[["modelo", "auc_roc", "auc_pr", "sensibilidad", "especificidad", "f1"]].round(4).to_markdown(index=False)}

Mejor modelo por AUC-PR: **{mejor.modelo}** (AUC-PR = {mejor.auc_pr:.4f}).

**No se reporta la exactitud como métrica principal.** Con {prev:.1%} de eventos,
predecir "nadie tiene depresión" acierta el {(1 - prev):.1%} y es inútil.

## Variables más influyentes (SHAP)

{imp.head(8)[["etiqueta", "importancia_relativa"]].round(2).to_markdown(index=False)}

## Limitaciones

- **Diseño transversal:** no permite afirmaciones causales ni descartar
  causalidad reversa.
- **Discriminación moderada.** El AUC ronda 0,67-0,70: sirve para priorizar
  poblaciones, no para decidir sobre una persona.
- **Autorreporte.** El PHQ-9 es tamizaje, no diagnóstico clínico. Las
  condiciones crónicas también son autorreportadas.
- **Validez temporal y geográfica.** Entrenado con datos de 2025 en el Perú. No
  se ha validado en otros países ni en otras olas.
- **Región natural derivada** por altitud, no la clasificación oficial del INEI.
- **La altitud no entra en este modelo.** Se analiza aparte
  (`analisis_07_altitud.py`) porque su asociación con el desenlace se examina
  como pregunta propia, no como predictor a optimizar.
- **La numeración de los ítems no es la canónica.** En la ENDES el ítem de
  pensamientos de hacerse daño es `QS700H`, no `QS700I`: el cuestionario coloca
  «se sintió mal consigo mismo» al final. Cualquier reanálisis que asuma el
  orden estándar del PHQ-9 señalará el ítem equivocado.

## Usos prohibidos

- Diagnosticar depresión en una persona concreta.
- Decidir acceso a tratamiento, seguros, empleo o cualquier prestación.
- Tamizar sin ofrecer derivación a atención profesional.
- Presentar la probabilidad como certeza, o sin el intervalo de incertidumbre.
- Analizar o publicar el ítem de autolesión (`QS700H`) como resultado
  independiente.

## Consideraciones éticas

{cfg.LINEA_AYUDA}

No se publican datos individuales. El modelo se entrenó sobre microdatos
públicos y anonimizados del INEI.

---

*Generado por `codigo/scripts/analisis_06_ml.py`. Semilla {cfg.RANDOM_SEED}.*
"""
    (cfg.MODELOS / "model_card.md").write_text(texto, encoding="utf-8")


def main() -> None:
    """Entrena, valida, interpreta y documenta los modelos predictivos."""
    dio.configurar_logging()
    df = pd.read_parquet(cfg.DATASET_FINAL)
    base = df[df.en_analisis == 1].copy()
    X, y, grupos, etiquetas = preparar(base)
    razon = (y == 0).sum() / (y == 1).sum()
    print(f"n = {len(y):,} · eventos = {y.sum():,} ({y.mean():.2%}) · "
          f"conglomerados = {len(np.unique(grupos)):,} · razón de desbalance = {razon:.1f}\n")

    print("Validación cruzada estratificada y agrupada por conglomerado:")
    modelos = construir_modelos(razon)
    resultados, predicciones = validar(modelos, X, y, grupos)
    dio.guardar_tabla(resultados, "tabla_28_comparacion_modelos_ml",
                      "Comparación de modelos predictivos con validación agrupada")
    figura_comparacion(y, predicciones, resultados)

    # El mejor modelo de árboles, para SHAP
    candidatos = resultados[resultados.modelo.isin(["XGBoost", "LightGBM", "Random Forest"])]
    nombre_mejor = candidatos.loc[candidatos.auc_pr.idxmax(), "modelo"]
    print(f"\nMejor modelo de árboles por AUC-PR: {nombre_mejor}")
    final = __import__("copy").deepcopy(modelos[nombre_mejor])
    final.fit(X, y)

    imp, valores, muestra = analisis_shap(final, X, etiquetas)
    dio.guardar_tabla(imp, "tabla_29_importancia_shap", "Importancia global de variables (SHAP)")
    figura_shap(imp, valores, muestra)
    print("\nVariables más influyentes (SHAP):")
    print(imp.head(8)[["etiqueta", "shap_medio_abs", "importancia_relativa"]].to_string(index=False))

    comp = comparar_shap_con_or(imp)
    if len(comp):
        dio.guardar_tabla(comp, "tabla_30_shap_vs_or",
                          "Contraste entre el ranking SHAP y el de los OR ajustados")
        print("\nContraste SHAP frente a OR ajustados:")
        print(comp.to_string(index=False))
        coincide = (comp.diferencia_rango.abs() <= 3).mean() * 100
        print(f"\n  El {coincide:.0f} % de las variables coincide dentro de tres posiciones "
              f"entre ambos rankings.")

    # Solo se persiste la logística: es la que va a la API (§13.2)
    logistica_final = __import__("copy").deepcopy(modelos["Logística regularizada"])
    logistica_final.fit(X, y)
    joblib.dump({"modelo": logistica_final, "columnas": list(X.columns),
                 "etiquetas": etiquetas, "referencias": REFERENCIAS,
                 "predictores": PREDICTORES},
                cfg.MODELOS / "modelo_logistico.joblib")
    (cfg.MODELOS / "shap_precalculado.json").write_text(
        json.dumps({"importancia": imp.head(14).to_dict("records")},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    escribir_model_card(resultados, imp, len(y), float(y.mean()))
    print("\nModelos predictivos completados. Ficha del modelo escrita.")


if __name__ == "__main__":
    main()
