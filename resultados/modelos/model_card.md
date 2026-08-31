# Ficha del modelo — Tamizaje de riesgo de depresión (ENDES 2025)

## Uso previsto

Instrumento de **tamizaje epidemiológico poblacional** con fines académicos y de
salud pública. Estima la probabilidad de que una persona presente sintomatología
depresiva moderada o grave (PHQ-9 ≥ 10) a partir de características
sociodemográficas, conductuales y clínicas.

> Esta herramienta estima riesgo epidemiológico con fines académicos y de salud pública. No constituye un diagnóstico médico ni reemplaza la evaluación de un profesional de salud mental.

## Población

Personas de 15 años a más residentes en el Perú, según la ENDES 2025 del INEI.
Muestra de entrenamiento: 28,553 personas, prevalencia del desenlace 6.21%.

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

| modelo                           |   auc_roc |   auc_pr |   sensibilidad |   especificidad |     f1 |
|:---------------------------------|----------:|---------:|---------------:|----------------:|-------:|
| Logística regularizada           |    0.6727 |   0.1172 |         0.1467 |          0.9435 | 0.1467 |
| Random Forest                    |    0.6839 |   0.1187 |         0.158  |          0.9443 | 0.158  |
| XGBoost                          |    0.6668 |   0.1153 |         0.1524 |          0.9439 | 0.1524 |
| LightGBM                         |    0.6549 |   0.1111 |         0.1518 |          0.9439 | 0.1518 |
| Modelo trivial (predice 'nadie') |    0.5    |   0.0621 |         0      |          1      | 0      |

Mejor modelo por AUC-PR: **Random Forest** (AUC-PR = 0.1187).

**No se reporta la exactitud como métrica principal.** Con 6.2% de eventos,
predecir "nadie tiene depresión" acierta el 93.8% y es inútil.

## Variables más influyentes (SHAP)

| etiqueta                                          |   importancia_relativa |
|:--------------------------------------------------|-----------------------:|
| es_mujer                                          |                  37.2  |
| edad                                              |                  12.93 |
| region_natural: Selva (ref. Costa)                |                   7.67 |
| educacion_grupo: Primaria o menos (ref. Superior) |                   6.38 |
| hta_dx                                            |                   5.79 |
| imc                                               |                   5.37 |
| grupo_etario: 60+ (ref. 30-39)                    |                   4.25 |
| es_rural                                          |                   4.07 |

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

Si te sientes mal, busca ayuda profesional. En el Perú puedes llamar gratuitamente a la Línea 113, opción 5 (salud mental), del MINSA.

No se publican datos individuales. El modelo se entrenó sobre microdatos
públicos y anonimizados del INEI.

---

*Generado por `codigo/scripts/analisis_06_ml.py`. Semilla 42.*
