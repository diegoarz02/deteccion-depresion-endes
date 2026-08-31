"""Genera los nueve notebooks del proyecto.

Los notebooks **narran**: abren con el objetivo, llaman a las funciones de
``codigo/src/depresion`` y cierran con conclusiones. La lógica pesada no vive
aquí, de modo que el análisis se puede ejecutar sin abrir Jupyter y los
notebooks no se convierten en una copia divergente del código.

Uso
---
    python codigo/scripts/generar_notebooks.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402

DESTINO = cfg.RAIZ / "codigo" / "notebooks"

CABECERA = """import sys, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path.cwd().parents[1] / "codigo" / "src"))
sys.path.insert(0, str(Path.cwd().parents[1] / "codigo" / "scripts"))

import numpy as np
import pandas as pd
from depresion import config as cfg, io as dio, viz
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 60)
viz.aplicar_tema()
print("Proyecto:", cfg.RAIZ.name)"""


_CONTADOR = {"n": 0}


def _id() -> str:
    """Genera un identificador de celda estable y reproducible.

    nbformat exige el campo ``id`` desde la versión 4.5. Se numera en orden en
    lugar de usar aleatoriedad para que regenerar los notebooks no produzca un
    diff espurio en cada ejecución.
    """
    _CONTADOR["n"] += 1
    return f"celda-{_CONTADOR['n']:04d}"


def md(texto: str) -> dict:
    """Celda de markdown."""
    return {"cell_type": "markdown", "id": _id(), "metadata": {},
            "source": texto.splitlines(keepends=True)}


def code(texto: str) -> dict:
    """Celda de código, sin salida guardada."""
    return {"cell_type": "code", "id": _id(), "execution_count": None, "metadata": {},
            "outputs": [], "source": texto.splitlines(keepends=True)}


def notebook(celdas: list[dict]) -> dict:
    """Envuelve las celdas en la estructura de un .ipynb."""
    return {
        "cells": celdas,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.14.5"},
        },
        "nbformat": 4, "nbformat_minor": 5,
    }


def encabezado(numero: str, titulo: str, objetivo: str, entradas: str, salidas: str) -> list[dict]:
    """Bloque inicial común: título, objetivo, entradas y salidas."""
    return [
        md(f"""# {numero} · {titulo}

**Objetivo.** {objetivo}

| | |
|---|---|
| **Entradas** | {entradas} |
| **Salidas** | {salidas} |

> Proyecto: *Modelamiento epidemiológico de la depresión en la población peruana de 15 y
> más años (ENDES 2025)* · Epidemiología 2026-2 · UNMSM
"""),
        code(CABECERA),
    ]


NOTEBOOKS: dict[str, list[dict]] = {}

# ── 01 ────────────────────────────────────────────────────────────────
NOTEBOOKS["01_ingesta_y_union.ipynb"] = [
    *encabezado(
        "01", "Ingesta y unión de las bases",
        "Leer los microdatos del INEI y unirlos por `HHID`, verificando el match antes de "
        "seguir. El estrato solo existe en RECH0, así que esta unión es requisito para "
        "poder declarar el diseño muestral.",
        "`CSALUD01_2025.sav`, `RECH0_2025.sav`",
        "DataFrame unido en memoria; el dataset final lo produce el notebook 03"),
    md("## Lectura\n\nSe lee con `apply_value_formats=False` **deliberadamente**: aplicar "
       "las etiquetas destruiría los 33 casos de violencia severa de `QS711`, cuya "
       "codificación real (3, 4) no coincide con el diccionario del INEI (8, 9)."),
    code("""csalud, meta_cs = dio.leer_sav(cfg.ARCHIVO_CSALUD)
rech0, meta_r0 = dio.leer_sav(cfg.ARCHIVO_RECH0)
meta = meta_cs.combinar(meta_r0)
print(f"CSALUD01: {csalud.shape}")
print(f"RECH0   : {rech0.shape}")"""),
    md("## Verificación de la llave\n\nSi el match cae por debajo del 99 %, el pipeline se "
       "detiene: no tiene sentido analizar una muestra que perdió parte de su geografía."),
    code("""izq = csalud[cfg.LLAVE].astype(str).str.strip()
der = rech0[cfg.LLAVE].astype(str).str.strip()
print(f"Ejemplo de HHID: {csalud[cfg.LLAVE].iloc[0]!r}")
print(f"Match: {izq.isin(set(der)).mean():.4%}")
print(f"Duplicados en RECH0: {der.duplicated().sum()}")"""),
    code("""from depresion import limpieza as lim
df = lim.unir_bases(csalud, rech0)
print(f"Tras la unión: {df.shape}")
df[[cfg.VAR_ESTRATO, cfg.VAR_DEPARTAMENTO, cfg.VAR_AREA, cfg.VAR_ALTITUD]].isna().sum()"""),
    md("""## Conclusiones

- Match del **100,00 %** (33 569 de 33 569), sin duplicados. El `.str.strip()` no era
  estrictamente necesario —ambas claves traen el mismo relleno de 15 caracteres— pero se
  aplica por robustez.
- Tras la unión hay **0 faltantes** en estrato, departamento, área y altitud.
- `HV022` (estrato) vive **solo en RECH0**: sin esta unión no se puede declarar el diseño.
"""),
]

# ── 02 ────────────────────────────────────────────────────────────────
NOTEBOOKS["02_calidad_y_limpieza.ipynb"] = [
    *encabezado(
        "02", "Calidad de datos y limpieza",
        "Auditar la calidad variable por variable, verificar la lógica de saltos contra los "
        "datos y limpiar los códigos especiales **sin recodificar por convención**.",
        "DataFrame unido del notebook 01",
        "`tabla_01_calidad_datos`, `tabla_02_verificacion_saltos`, "
        "`tabla_03_inventario_codigos_8_9`"),
    code("""from depresion import limpieza as lim
from construir_dataset import auditoria_calidad
csalud, meta_cs = dio.leer_sav(cfg.ARCHIVO_CSALUD)
rech0, meta_r0 = dio.leer_sav(cfg.ARCHIVO_RECH0)
meta = meta_cs.combinar(meta_r0)
df = lim.unir_bases(csalud, rech0)"""),
    md("## Verificación de la lógica de saltos\n\nUna *violación* es un caso con dato "
       "presente sin cumplir el filtro que debería habilitarlo. Cero violaciones significa "
       "que el `NaN` es «no aplica», no «no respondió» — y por tanto **no se imputa**."),
    code("""saltos = lim.verificar_saltos(df)
saltos[["cadena", "filtro", "variable", "esperados", "presentes", "violaciones", "veredicto"]]"""),
    md("""## La trampa de los códigos 8 y 9

La regla habitual dice que `8 = No sabe` y `9 = Rehúsa`. Es cierta para la mayoría de
variables, pero **no para todas**, y aplicarla a ciegas corrompe los datos."""),
    code("""inv = lim.inventariar_codigos_especiales(df, meta)
print(f"Variables con código 8 o 9: {len(inv)}")
print("\\nExcepciones — donde el código NO significa dato faltante:")
inv[inv.decision.str.startswith("REVISAR")][
    ["variable", "descripcion", "etiqueta_8", "etiqueta_9"]].head(10)"""),
    md("### El caso de `QS711`\n\nEl diccionario del INEI declara los códigos 1, 2, 8 y 9. "
       "Los datos graban 1, 2, 3 y 4. Es un **error de etiquetado en la fuente oficial**."),
    code("""print("QS710 — datos: ", sorted(df.QS710.dropna().unique()))
print("QS710 — etiquetas:", meta.valores("QS710"))
print("\\nQS711 — datos: ", sorted(df.QS711.dropna().unique()))
print("QS711 — etiquetas:", meta.valores("QS711"))
print(f"\\n¿Existen los códigos 8 o 9 en QS711? {df.QS711.isin([8, 9]).any()}")
print(f"Casos en las categorías severas (3, 4): {int(df.QS711.isin([3, 4]).sum())}")"""),
    code("""df, informe_qs711 = lim.corregir_qs711(df)
df, bitacora = lim.limpiar_codigos_faltantes(df, meta)
df, antro = lim.limpiar_antropometria(df)
print(bitacora.accion.value_counts().to_string())
antro"""),
    md("""## Conclusiones

- Las **siete cadenas de saltos** son estructuralmente limpias: cero violaciones.
- De 127 variables con código 8 o 9, se limpiaron **87** y quedaron **40 intactas**.
  Entre las intactas: `QSINTM` y `QS22M` (8 = agosto, 9 = septiembre), `QS25AA`
  (lengua materna) y variables de conteo donde 8 y 9 son cantidades reales.
- `QS711` conserva su escala 1-4 y sus 33 casos severos.
- El umbral de no-medición (`≥ 900`) se aplica **solo** a peso, talla y perímetro
  abdominal. La presión arterial no usa ese código.
"""),
]

# ── 03 ────────────────────────────────────────────────────────────────
NOTEBOOKS["03_construccion_variables.ipynb"] = [
    *encabezado(
        "03", "Construcción de variables",
        "Construir el desenlace y las exposiciones codificando el «no aplica» de forma "
        "explícita, y guardar el dataset único del proyecto.",
        "DataFrame limpio",
        "`datos/final/data.parquet`, `tabla_00_diccionario`, `tabla_04_flujograma_strobe`"),
    md("Todo este notebook se resume en un script reproducible. Se ejecuta aquí para poder "
       "inspeccionar los pasos intermedios."),
    code("""%run ../scripts/construir_dataset.py"""),
    code("""df = pd.read_parquet(cfg.DATASET_FINAL)
print(f"Dataset: {df.shape}")
print((cfg.DATOS_FINAL / "data_hash.txt").read_text())"""),
    md("## Reglas de construcción\n\nCada variable derivada guarda la regla exacta que la "
       "produjo. Es lo que permite replicar el dataset en R o SPSS."),
    code("""from depresion import variables as var
for nombre, regla in list(var.REGLAS.items())[:12]:
    print(f"\\n{nombre}\\n  {regla}")"""),
    md("### El caso del alcohol\n\nEl bloque tiene saltos del tipo «si responde Sí, salta la "
       "siguiente»: el criterio ya quedó satisfecho. Contar ítems en crudo penalizaría "
       "justamente a los casos más graves, así que se agrupan por criterio con lógica OR."),
    code("""print(var.REGLAS["n_criterios_dependencia"])
print()
print(df.alcohol_categoria.value_counts(dropna=False).to_string())"""),
    md("""## Conclusiones

- Dataset de **33 569 × 71**, con hash SHA-256 para versionarlo.
- Población de análisis: **30 226** (`en_analisis == 1`).
- El flujograma STROBE documenta cada exclusión con su N y su motivo.
- `violencia_fisica` **no** se codifica como 0 para quien no tuvo pareja: es una
  subpoblación distinta, no un cero.
"""),
]

# ── 04 ────────────────────────────────────────────────────────────────
NOTEBOOKS["04_screening_de_variables.ipynb"] = [
    *encabezado(
        "04", "Screening de variables",
        "Decidir qué variables entran al modelo evaluando cobertura, varianza, celdas "
        "mínimas, asociación bivariada, colinealidad y rol causal. **Ninguna se excluye por "
        "tener p > 0,05**: eso sería p-hacking.",
        "`data.parquet`",
        "`tabla_05_screening_variables`, `tabla_05c_gvif`"),
    code("""%run ../scripts/analisis_01_screening.py"""),
    code("""scr = pd.read_csv(cfg.TABLAS / "tabla_05_screening_variables.csv")
scr[["variable", "cobertura_pct", "pct_modal", "celda_minima", "or_crudo", "p", "DECISION"]]"""),
    md("## Justificación de cada decisión\n\nRegistrar el motivo de **inclusión** importa "
       "tanto como el de exclusión: sin eso, las reincorporaciones quedan huérfanas."),
    code("""for _, r in scr.iterrows():
    print(f"\\n{r.variable}  →  {r.DECISION}\\n   {r.JUSTIFICACION}")"""),
    md("## Colinealidad\n\nSe usa el **GVIF** de Fox y Monette, no el VIF corriente: los "
       "indicadores de un mismo factor están correlacionados por construcción y darían VIF "
       "de 8-15 sin que exista problema real."),
    code("""pd.read_csv(cfg.TABLAS / "tabla_05c_gvif.csv")"""),
    md("""## Conclusiones

- **13 variables incluidas**, 3 excluidas, 4 a análisis de sensibilidad.
- GVIF comparable máximo **1,18**: no hay colinealidad problemática.
- `recibio_tratamiento_sm` se excluye por **causalidad reversa**, no por su p.
- `violencia_fisica` entra como **subpoblación**, no como variable con faltantes.
"""),
]

# ── 05 ────────────────────────────────────────────────────────────────
NOTEBOOKS["05_descriptivo_y_frecuencias.ipynb"] = [
    *encabezado(
        "05", "Descriptivo y medidas de frecuencia",
        "Estimar prevalencias ponderadas con el diseño muestral complejo, describir la "
        "muestra y cuantificar la brecha de atención.",
        "`data.parquet`",
        "`tabla_06` a `tabla_11`, `fig_01` a `fig_05`, mapa coroplético"),
    code("""%run ../scripts/analisis_02_descriptivo.py"""),
    md("## Ficha del diseño\n\nEl efecto de diseño dice cuánta información real aporta la "
       "muestra. Un deff de 3 significa que 30 000 encuestas informan como unas 10 000 "
       "tomadas al azar."),
    code("""pd.read_csv(cfg.TABLAS / "tabla_06_ficha_diseno_muestral.csv")"""),
    code("""pd.read_csv(cfg.TABLAS / "tabla_08_prevalencias_ponderadas.csv")[
    ["variable", "categoria", "n", "prevalencia", "ic_95", "deff"]]"""),
    md("## Brecha de atención"),
    code("""brecha = pd.read_csv(cfg.TABLAS / "tabla_11_brecha_atencion.csv")
print(f"Brecha nacional: {brecha.brecha.iloc[0]:.1f} %")
brecha"""),
    md("""## Conclusiones

- Prevalencia nacional ponderada: **6,98 %** (IC 95 % 6,49-7,51).
- **Mujeres 9,87 % frente a hombres 3,86 %**: la razón es de 2,6.
- Curva en **U por edad**: 8,37 % en 15-19, mínimo 4,25 % en 30-39, 9,80 % en 60+.
- Gradiente educativo: de 8,77 % (primaria o menos) a 5,28 % (superior).
- Sierra 8,04 %, Costa 6,90 %, Selva 4,97 %.
- **Brecha de atención del 87,6 %**, por encima del 80 % en todos los subgrupos.
- Alfa de Cronbach de los nueve ítems: **0,875**.
"""),
]

# ── 06 ────────────────────────────────────────────────────────────────
NOTEBOOKS["06_asociacion_OR_y_confusion.ipynb"] = [
    *encabezado(
        "06", "Asociación, sesgo y confusión",
        "Estimar OR crudos y razones de prevalencia, y demostrar con Mantel-Haenszel cómo "
        "el ajuste cambia —y a veces invierte— las conclusiones.",
        "`data.parquet`",
        "`tabla_12` a `tabla_15`, `fig_06` a `fig_08`, DAG causal"),
    code("""%run ../scripts/analisis_03_asociacion.py"""),
    md("## OR frente a RP\n\nEn un transversal el OR sobreestima la razón de prevalencias "
       "tanto más cuanto mayor sea la prevalencia. Con un 7 %, la teoría predice que deben "
       "parecerse. Comprobarlo es un punto de rigor, no un trámite."),
    code("""t = pd.read_csv(cfg.TABLAS / "tabla_12_or_y_rp.csv")
t[["exposicion", "or_formato", "rp_formato", "sobreestimacion_or_pct", "p_fdr"]]"""),
    md("## El caso del tabaco\n\nEs el mejor ejemplo de confusión que ofrece este conjunto "
       "de datos."),
    code("""conf = pd.read_csv(cfg.TABLAS / "tabla_14_confusion_mantel_haenszel.csv")
conf[conf.variable == "fuma_12m"][
    ["estratificador", "or_crudo", "or_mh", "cambio_pct", "p_homogeneidad", "veredicto"]]"""),
    md("""## Conclusiones

- La sobreestimación media del OR sobre la RP es del **5,3 %**: con prevalencia baja
  ambas medidas convergen, como predice la teoría.
- **El tabaco parecía protector** (OR crudo 0,72). Ajustado por sexo: **OR 1,17**. Los
  hombres fuman mucho más y tienen menos depresión.
- El consumo frecuente de alcohol sigue el mismo patrón: 0,75 → 1,00.
- Con N ≈ 30 000, la prueba de homogeneidad detecta diferencias mínimas. Que sea
  significativa no implica que la modificación de efecto sea relevante: hay que mirar la
  magnitud, no solo el valor p.
"""),
]

# ── 07 ────────────────────────────────────────────────────────────────
NOTEBOOKS["07_anova_y_regresion_lineal.ipynb"] = [
    *encabezado(
        "07", "ANOVA de un factor y regresión lineal",
        "Contrastar el puntaje PHQ-9 entre grupos y ajustar la regresión lineal, "
        "**declarando** que el desenlace viola normalidad y homocedasticidad en vez de "
        "esconderlo.",
        "`data.parquet`",
        "`tabla_16` a `tabla_20`, `fig_09`, `fig_10`"),
    code("""%run ../scripts/analisis_04_anova_lineal.py"""),
    code("""anovas = pd.read_csv(cfg.TABLAS / "tabla_16_anova.csv")
anovas[["factor_etiqueta", "F", "p_anova", "F_welch", "p_welch", "H_kruskal", "p_kruskal",
        "eta2", "levene_cumple", "normalidad_cumple", "prueba_valida", "magnitud_efecto"]]"""),
    md("## Los cuatro tratamientos del sesgo"),
    code("""pd.read_csv(cfg.TABLAS / "tabla_18_comparacion_modelos_lineales.csv")"""),
    code("""pd.read_csv(cfg.TABLAS / "tabla_19_supuestos_regresion.csv")"""),
    md("""## Conclusiones

- Los tres factores fallan homocedasticidad **y** normalidad, así que la prueba válida es
  **Kruskal-Wallis** en los tres casos.
- Los tamaños de efecto son pequeños: η² = 0,024 para grupo etario, 0,010 para nivel
  educativo y 0,006 para región. Con N grande, «significativo» y «relevante» no son lo
  mismo.
- La transformación raíz cuadrada baja la asimetría de los residuos de **2,35 a 0,79**,
  pero no elimina el exceso de ceros.
- La sobredispersión es de **6,06**, así que entre las alternativas de conteo la correcta
  es la **binomial negativa**, no Poisson.
- El R² del modelo lineal es 0,054. Es bajo, y es honesto: la depresión no se explica con
  once variables sociodemográficas y clínicas.
- **La conclusión sustantiva se apoya en la logística**, que no exige normalidad del
  desenlace.
"""),
]

# ── 08 ────────────────────────────────────────────────────────────────
NOTEBOOKS["08_regresion_logistica.ipynb"] = [
    *encabezado(
        "08", "Regresión logística — modelo principal",
        "Estimar los OR ajustados con el diseño muestral complejo, verificar el ajuste y "
        "exportar los coeficientes para el boletín y la API.",
        "`data.parquet`",
        "`tabla_21` a `tabla_27`, `fig_11`, `fig_12`, `coeficientes_logistico.json`"),
    code("""%run ../scripts/analisis_05_logistica.py"""),
    md("## Crudo frente a ajustado"),
    code("""pd.read_csv(cfg.TABLAS / "tabla_21_modelos_por_bloques.csv")[
    ["exposicion", "or_crudo", "or_ajustado", "cambio_pct", "cambia_de_direccion"]]"""),
    md("## Modelo completo"),
    code("""log = pd.read_csv(cfg.TABLAS / "tabla_22_logistica_diseno_complejo.csv")
log[["etiqueta", "or_formato", "p", "significativo"]]"""),
    md("## Diagnóstico"),
    code("""pd.read_csv(cfg.TABLAS / "tabla_24_diagnostico_logistica.csv")"""),
    md("""## Conclusiones

- n = 28 553, 1 772 eventos, **EPV = 104**: holgadísimo frente al umbral clásico de 10.
- Se usa `svy.GLM`, que aplica los **grados de libertad del diseño** (2 994 = conglomerados
  menos estratos) y contrastes t y F, como `svyglm` de R.
- **Consumo problemático de alcohol: OR 6,07** (3,41-10,82), el más alto del modelo.
- Sexo femenino OR 2,94; edad 15-19 OR 2,11; Selva OR 0,67 frente a Costa.
- El tabaco pasa de 0,83 crudo a **1,44 ajustado**: cambia de dirección.
- Violencia física en la subpoblación con pareja: **OR 3,86** (2,74-5,44).
- AUC 0,667: discriminación aceptable. Sirve para priorizar poblaciones, no para decidir
  sobre una persona.
- Hosmer-Lemeshow rechaza (p = 0,006), pero con N grande es hipersensible; la curva de
  calibración y el Brier son la referencia.
- Box-Tidwell rechaza la linealidad del logit en la edad continua: **justifica usar el
  grupo etario categorizado**, que es lo que hace el modelo.
"""),
]

# ── 09 ────────────────────────────────────────────────────────────────
NOTEBOOKS["09_modelo_predictivo_ml.ipynb"] = [
    *encabezado(
        "09", "Modelos predictivos e interpretabilidad",
        "Extra de portafolio, separado del análisis inferencial: comparar algoritmos con "
        "validación agrupada por conglomerado y contrastar SHAP con los OR.",
        "`data.parquet`",
        "`tabla_28` a `tabla_30`, `fig_13`, `fig_14`, `model_card.md`"),
    md("""> **Esta sección responde otra pregunta.** El análisis epidemiológico pregunta
> «¿cuál es el efecto de X?»; aquí se pregunta «¿se puede ordenar el riesgo?». Son
> objetivos distintos y no se sustituyen."""),
    code("""%run ../scripts/analisis_06_ml.py"""),
    code("""pd.read_csv(cfg.TABLAS / "tabla_28_comparacion_modelos_ml.csv")[
    ["modelo", "auc_roc", "auc_pr", "sensibilidad", "especificidad", "f1", "exactitud"]]"""),
    md("""## El contraste que importa

¿El modelo aprende lo mismo que dice la epidemiología? Comparar el ranking de SHAP con el
de los OR ajustados responde a eso, y la discrepancia es más informativa que la
coincidencia."""),
    code("""pd.read_csv(cfg.TABLAS / "tabla_30_shap_vs_or.csv")"""),
    md("""## Conclusiones

- AUC-ROC entre 0,65 y 0,68 según el algoritmo; AUC-PR de 0,11 a 0,12 frente a 0,062 del
  azar, es decir **1,9 veces mejor**.
- La validación se agrupa por conglomerado: repartir personas del mismo conglomerado entre
  entrenamiento y prueba habría inflado el rendimiento.
- **No se reporta la exactitud como métrica principal.** Con 6,2 % de eventos, responder
  «nadie tiene depresión» acierta el 93,8 %.
- **SHAP y los OR discrepan, y ahí está lo interesante.** El consumo problemático de
  alcohol es el **primero por OR (6,07)** y el **decimoquinto por SHAP**: afecta a solo 304
  personas, así que un efecto grande sobre muy pocos aporta poco a la predicción media.
  El sexo es lo contrario: efecto moderado sobre media población, y domina el SHAP.
- La lección: **un OR grande no implica una variable útil para predecir**, y una variable
  importante para predecir no es necesariamente la más relevante para intervenir.
"""),
]


def main() -> None:
    """Escribe los nueve notebooks."""
    DESTINO.mkdir(parents=True, exist_ok=True)
    for nombre, celdas in NOTEBOOKS.items():
        ruta = DESTINO / nombre
        ruta.write_text(json.dumps(notebook(celdas), ensure_ascii=False, indent=1),
                        encoding="utf-8")
        print(f"  {nombre:38s} {len(celdas):2d} celdas")
    print(f"\n{len(NOTEBOOKS)} notebooks escritos en {DESTINO}")


if __name__ == "__main__":
    main()
