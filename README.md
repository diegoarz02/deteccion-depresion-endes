# Modelamiento epidemiológico de la depresión en la población peruana de 15 y más años

**Factores conductuales, sociales y clínicos asociados — ENDES 2025**

Análisis epidemiológico completo sobre los microdatos de la Encuesta Demográfica y de
Salud Familiar 2025 del INEI, respetando el diseño muestral complejo (bietápico,
estratificado, por conglomerados), con boletín interactivo, API y agente conversacional.

> **Aviso.** Este trabajo estima riesgo epidemiológico con fines académicos y de salud
> pública. No constituye un diagnóstico médico ni reemplaza la evaluación de un profesional
> de salud mental. Si te sientes mal, busca ayuda: en el Perú puedes llamar gratuitamente a
> la **Línea 113, opción 5 (salud mental)** del MINSA.

---

## Hallazgos principales

| Indicador | Valor |
|---|---|
| Prevalencia de depresión (PHQ-9 ≥ 10), ponderada | **6,98 %** (IC 95 % 6,49–7,51) |
| **Brecha de atención** | **87,6 %** no recibió atención profesional |
| Razón mujer / hombre | 9,87 % frente a 3,86 % |
| Región con mayor prevalencia | Sierra 8,04 % · Costa 6,90 % · Selva 4,97 % |
| Departamento extremo | Puno 12,8 % · Ucayali 1,1 % |
| Gradiente educativo | Primaria o menos 8,77 % → Superior 5,28 % |
| OR ajustado más alto | Consumo problemático de alcohol **6,07** (3,41–10,82) |
| Efecto de diseño | deff 3,09 · muestra efectiva 9 774 |

La prevalencia por edad describe una **curva en U**: 8,37 % en 15-19 años, mínimo 4,25 %
en 30-39 y máximo 9,80 % en 60 o más.

### El resultado que más enseña

**El tabaco parecía protector.** OR crudo **0,72**; ajustado por sexo, **1,17**; en el
modelo multivariable completo, **1,44**. Los hombres fuman mucho más y tienen menos
depresión, así que el sexo confundía por completo la asociación. Lo mismo ocurre con el
consumo frecuente de alcohol (0,75 → 1,00). Reportar el OR crudo habría llevado a una
conclusión invertida.

*Todas las cifras provienen de código ejecutado; ninguna se transcribió a mano.*

---

## Datos

| Fuente | Contenido | Dimensiones |
|---|---|---|
| `CSALUD01_2025.sav` | Cuestionario de Salud, personas de 15 años a más | 33 569 × 262 |
| `RECH0_2025.sav` | Registro del hogar: geografía y diseño muestral | 37 331 × 44 |

Se unen por `HHID` (match verificado: **100,00 %**, 0 duplicados).

**Los microdatos no se versionan en este repositorio.** Descárgalos del INEI en
<http://iinei.inei.gob.pe/microdatos/> (ENDES 2025, módulos CSALUD01 y RECH0) y colócalos
en `datos/crudos/`, o ajusta `FUENTE_SAV` en `codigo/src/depresion/config.py`.

El GeoJSON de departamentos procede de
[juaneladio/peru-geojson](https://github.com/juaneladio/peru-geojson); los 25
departamentos cruzan sin excepción tras normalizar los nombres.

### Diseño muestral

Confirmado en la ficha técnica oficial (pág. 12):

```
conglomerado = QHCLUSTER    estrato = HV022    peso = Peso15_AMAS / 1 000 000
```

3 252 conglomerados, 240 estratos, conglomerados anidados en estratos. Los **18 estratos
con un solo conglomerado** se tratan con centrado en la media general, equivalente a
`options(survey.lonely.psu = "adjust")` de R.

> ⚠️ **El ponderador es relativo, no un factor de expansión.** La suma de pesos escalados
> es 36 173, no la población peruana de 15+ (≈26 millones). Sirve para prevalencias,
> medias, OR y errores estándar; **no** para totales poblacionales absolutos. Por eso en
> este trabajo no aparece ninguna cifra del tipo «X millones de peruanos».

---

## Cuatro decisiones que cambian los resultados

1. **`QS711` tiene un error de etiquetado en la fuente oficial.** El diccionario del INEI
   declara los códigos 1, 2, 8 y 9; los datos graban 1, 2, 3 y 4. Aplicar las etiquetas
   destruiría los 33 casos de violencia más severa. Se lee en la escala 1-4 de `QS710`, su
   pregunta gemela.

2. **`QS702`, `QS703` y `QS704A–I` son fuga de información.** La cobertura de `QS702`
   (49,46 %) es idéntica al porcentaje con `phq9_score > 0`: la cobertura *es* el
   desenlace. Quedan fuera del dataset, no solo del modelo, y un test lo verifica.

3. **El bloque de alcohol salta la siguiente pregunta cuando respondes «sí».** Contar
   ítems en crudo penalizaría a los casos más graves, cuyo `NaN` significa «ya cumplió el
   criterio». Se agrupan por criterio con lógica OR.

4. **La región natural se deriva por altitud del conglomerado**, no por departamento,
   porque la altitud es fuertemente bimodal dentro de Áncash (42 % bajo 500 m y 55 % sobre
   2 300 m), La Libertad y Arequipa.

La auditoría inicial completa está en [`HALLAZGOS_FASE_0.md`](HALLAZGOS_FASE_0.md) y la
bitácora razonada en [`docs/decisiones_metodologicas.md`](docs/decisiones_metodologicas.md).

---

## Cómo reproducir

```bash
python -m venv .venv && source .venv/Scripts/activate   # Windows (Git Bash)
pip install -r requirements.txt

cp .env.example .env        # rellenar solo si se usa el agente con LLM

make data        # dataset único desde los .sav
make analisis    # las seis etapas del análisis epidemiológico
make boletin     # sitio estático en boletin/
make tests       # 39 tests (25 de datos + 14 de la API)
make api         # servidor local en http://localhost:8000
make agente      # demostración del agente LangGraph
```

El dataset se versiona por hash SHA-256 en `datos/final/data_hash.txt`: dos ejecuciones
sobre los mismos insumos producen el mismo hash.

---

## Estructura

```
├── datos/final/data.parquet      ← dataset único; todo el proyecto consume esto
├── codigo/
│   ├── src/depresion/            config · io · limpieza · variables · encuesta
│   │                             epi · supuestos · modelos · viz
│   ├── scripts/                  pipeline y análisis, uno por etapa
│   ├── notebooks/                01…09, narrativos
│   └── R/analisis_equivalente.R  réplica con survey, por si el docente la pide
├── resultados/
│   ├── tablas/                   30 tablas en csv + xlsx + tex
│   ├── figuras/                  14 figuras en png (300 dpi) + pdf
│   ├── mapas/                    coroplético interactivo
│   └── modelos/                  coeficientes, joblib y model_card.md
├── boletin/                      sitio estático de 5 páginas
├── api/                          FastAPI + Docker + render.yaml
├── agente/                       LangGraph con guardrails y modo degradado
├── docs/                         decisiones, diccionario, DAG, STROBE, grafo
└── tests/                        pytest
```

---

## Los cuatro productos

### 1. Análisis epidemiológico

Cubre el sílabo completo: medidas de frecuencia con diseño complejo, OR y razón de
prevalencias, sesgo y confusión por Mantel-Haenszel, ANOVA de un factor con verificación
de supuestos, regresión lineal y regresión logística.

Los supuestos se verifican y **se reportan aunque fallen**. El PHQ-9 tiene asimetría 2,4 y
la mitad de la muestra en cero, así que la regresión lineal cruda viola normalidad y
homocedasticidad: se comparan cuatro tratamientos (crudo, raíz cuadrada, errores robustos
HC3 y alternativa de conteo) y se explica por qué la conclusión sustantiva se apoya en la
logística.

### 2. Boletín HTML

Cinco páginas estáticas y autocontenidas, generadas por script desde `resultados/`, con
gráficos de Plotly, mapa coroplético, modo claro/oscuro y un **simulador de riesgo que
calcula la probabilidad en JavaScript en el navegador**, sin backend. Se publica en
cualquier hosting estático y no depende de que la API esté despierta.

```bash
make boletin && python -m http.server 8000 --directory boletin
```

### 3. API

FastAPI con validación estricta de Pydantic v2, carga del modelo en el *lifespan*,
limitación de tasa y CORS. Ver [`api/README.md`](api/README.md) para los ejemplos `curl`.

**Se despliega solo el modelo logístico**, por decisión de arquitectura: son 17
coeficientes en un JSON, arranca al instante y es el modelo del informe. XGBoost y SHAP se
quedan en el análisis local, y los valores SHAP del boletín están precalculados.

### 4. Agente LangGraph

Interpreta los resultados en lenguaje natural. Ocho nodos, aristas condicionales y un
**guardrail por reglas** que bloquea lenguaje diagnóstico, consejo farmacológico y
contenido sobre autolesión, con un tope de dos reescrituras.

**Funciona sin clave de API.** En modo degradado redacta con plantillas deterministas
construidas sobre las mismas cifras del modelo, así que el proyecto entero se puede
evaluar sin depender de un proveedor externo.

---

## Limitaciones

- **Diseño transversal.** Exposición y desenlace se miden a la vez: no se puede establecer
  temporalidad ni descartar causalidad reversa. Nada aquí debe leerse como efecto causal.
- **Autorreporte.** El PHQ-9 es tamizaje, no diagnóstico clínico. Las condiciones crónicas
  también son autorreportadas.
- **Sesgo de selección.** Se excluyó al 9,4 % sin PHQ-9 completo. Si la no respuesta se
  relaciona con la salud mental, la prevalencia estaría subestimada.
- **Región natural derivada** por altitud, no la clasificación oficial por distrito.
- **Discriminación moderada** (AUC 0,67): sirve para priorizar poblaciones, no para decidir
  sobre personas.
- **Sin totales poblacionales**, por lo dicho sobre el ponderador.
- Con N ≈ 30 000, las pruebas de bondad de ajuste y de homogeneidad rechazan por
  desviaciones triviales. Por eso todo estadístico va acompañado de su **tamaño de efecto**.

## Ética

- Los microdatos crudos no se suben al repositorio.
- No se publican datos individuales, solo agregados.
- El ítem `QS700H` (pensamientos de hacerse daño) forma parte del puntaje porque pertenece
  al instrumento, pero **no se analiza ni se destaca como desenlace independiente**.
- Toda salida dirigida a una persona orienta a buscar ayuda y menciona la Línea 113.
- Ninguna clave ni token aparece en el código, los notebooks o la configuración de
  despliegue.

---

## Equipo

Curso de Epidemiología 2026-2 · Facultad de Ciencias Matemáticas · Universidad Nacional
Mayor de San Marcos. Docente: Mg. Carlos Alberto Jaimes Velásquez.

Arapa Lazo Julio (22140218) · Araujo Villegas Diego Alonso (22140232) ·
Hidalgo Huachaca Dante (22140235) · Montero Tabori Melany (22140071) ·
Torres Matías (22140222) · Zegarra William (22140205).

## Referencias

- Basauri-Delgado, M., Mesía-Guevara, J.-A., & Saintila, J. (2025). *Influence of
  Sociodemographic, Socioeconomic, and Health Factors on Depression in the Peruvian
  Population: A Cross-Sectional Study*. **Journal of Primary Care & Community Health**, 16.
  DOI: [10.1177/21501319251342090](https://doi.org/10.1177/21501319251342090)
- Kroenke, K., Spitzer, R. L., & Williams, J. B. W. (2001). *The PHQ-9: Validity of a brief
  depression severity measure*. **Journal of General Internal Medicine**, 16(9), 606-613.
- Instituto Nacional de Estadística e Informática (2025). *Encuesta Demográfica y de Salud
  Familiar — ENDES 2025*. Ficha técnica y microdatos.
- Organización Mundial de la Salud (2023). *Trastornos depresivos (depresión)*.
- von Elm, E. et al. *STROBE Statement*. <https://www.strobe-statement.org/>
- Fox, J. & Monette, G. (1992). *Generalized collinearity diagnostics*. **JASA**, 87(417).
- Lumley, T. (2010). *Complex Surveys: A Guide to Analysis Using R*. Wiley.

## Licencia

MIT — ver [LICENSE](LICENSE).
