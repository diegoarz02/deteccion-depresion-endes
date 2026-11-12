# Modelamiento epidemiológico de la depresión en la población peruana de 15 y más años

**Factores conductuales, sociales y clínicos asociados — ENDES 2025**

Análisis epidemiológico completo sobre los microdatos de la Encuesta Demográfica y de
Salud Familiar 2025 del INEI, respetando el diseño muestral complejo (bietápico,
estratificado, por conglomerados), con boletín interactivo, API y agente conversacional.

> **Aviso.** Este trabajo estima riesgo epidemiológico con fines académicos y de salud
> pública. No constituye un diagnóstico médico ni reemplaza la evaluación de un profesional
> de salud mental. Si te sientes mal, busca ayuda: en el Perú puedes llamar gratuitamente a
> la **Línea 113, opción 5 (salud mental)** del MINSA.

## Ver el trabajo

| | |
|---|---|
| **Boletín** | https://diegoarz02.github.io/deteccion-depresion-endes/ |
| **Explorador «Gente como tú»** | https://depresion-endes.onrender.com |
| **Código** | https://github.com/diegoarz02/deteccion-depresion-endes |

El boletín son quince secciones que se leen de corrido, con dos bloques interactivos —uno
para explorar las tasas observadas por perfil y otro por departamento— que funcionan sin
servidor.

El explorador responde una pregunta distinta: cuántas personas parecidas a ti dieron
positivo en el tamizaje. Vive en el plan gratuito de Render, así que **la primera visita
tras un rato de inactividad tarda unos 50 segundos** en despertar el servicio; la propia
página lo avisa mientras tanto.

---

## Hallazgos principales

| Indicador | Valor |
|---|---|
| Prevalencia de depresión (PHQ-9 ≥ 10), ponderada | **6,98 %** (IC 95 % 6,49–7,51) |
| **Brecha de atención** | **87,6 %** no recibió atención profesional |
| Razón de prevalencias mujer / hombre | 2,6 (9,87 % frente a 3,86 %) |
| Región con mayor prevalencia | Sierra 8,04 % · Costa 6,90 % · Selva 4,97 % |
| Departamento extremo | Puno 12,8 % · Ucayali 1,1 % |
| Gradiente educativo | Primaria o menos 8,77 % → Superior 5,28 % |
| OR ajustado más alto | Consumo problemático de alcohol **6,07** (3,41–10,82); razón de prevalencias ajustada 4,80 |
| Impacto poblacional | Fracción atribuible del alcohol problemático 2,2 %; violencia de pareja 8,6 %; hipertensión 4,5 % |
| Efecto de diseño | deff 3,09 · muestra efectiva 9 774 |

La prevalencia por edad describe una **curva en U**: 8,37 % en 15-19 años, mínimo 4,25 %
en 30-39 y máximo 9,80 % en 60 o más.

### El resultado que más enseña

**El tabaco parecía protector.** Sin ponderar, el OR crudo es **0,72**; ajustado por sexo
(Mantel-Haenszel), **1,17**; en el modelo completo con el diseño de la encuesta, **1,41**. Con
los pesos de la encuesta la comparación cruda ya no se sostiene (OR 0,83, IC 0,66–1,05; Rao y
Scott p = 0,11). Los hombres fuman mucho más (27 % frente a 6 %) y tienen menos depresión, así
que el sexo confundía la asociación. Lo mismo ocurre con el consumo frecuente de alcohol (0,75 →
1,00 por Mantel-Haenszel). Reportar el OR crudo habría llevado a una conclusión invertida.

### La altitud: exposición y posible confusor

La altitud **no confunde** a ningún otro factor (el OR de cada uno cambia menos de 1,5 % al
añadirla; menos de 8 % sin la región natural). Su propio gradiente se mantiene al ajustar por las
características de las personas (OR por 1 000 m: 1,09; IC 95 % 1,03–1,15) y se **atenúa al comparar
dentro de un mismo departamento** (1,05; 0,96–1,14). Es una asociación con gradiente, no una causa:
el estudio es una foto y la correlación entre departamentos (r = 0,63) es un dato de grupo.

*Todas las cifras provienen de código ejecutado; ninguna se transcribió a mano.*

---

## Datos

| Fuente | Contenido | Dimensiones |
|---|---|---|
| `CSALUD01_2025.sav` | Cuestionario de Salud, personas de 15 años a más | 33 569 × 262 |
| `RECH0_2025.sav` | Registro del hogar: geografía y diseño muestral | 37 331 × 44 |

Se unen por `HHID` (match verificado: **100,00 %**, 0 duplicados).

**Los microdatos no se versionan en este repositorio.** Descárgalos del INEI en
<https://proyectos.inei.gob.pe/microdatos/> (ENDES 2025, módulos CSALUD01 y RECH0) y colócalos
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

Cada una de estas decisiones, con su justificación y las alternativas descartadas, está en
[`docs/decisiones_metodologicas.md`](docs/decisiones_metodologicas.md).

---

## Cómo reproducir

Desarrollado con **Python 3.14.5** en Windows 11. Las versiones de las librerías van
fijadas en `requirements.txt`.

### 1. Entorno

```bash
# Windows · Git Bash
python -m venv .venv
source .venv/Scripts/activate

# Windows · PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux o macOS
python3 -m venv .venv
source .venv/bin/activate
```

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt` incluye las herramientas de desarrollo (`pytest`, `ruff`). Para
desplegar el servicio se usa `api/requirements.txt`, que es mínimo a propósito: en Render
no caben pandas, geopandas ni shap dentro de los 512 MB del plan gratuito.

### 2. Microdatos

Los `.sav` de la ENDES 2025 no se versionan: son públicos y se descargan del
[portal de microdatos del INEI](https://proyectos.inei.gob.pe/microdatos/). Hacen falta
`CSALUD01_2025.sav`, `RECH0_2025.sav` y `RECH1_2025.sav`.

La ruta se indica por variable de entorno:

```bash
export ENDES_SAV="/ruta/a/los/sav"          # Git Bash
$env:ENDES_SAV = "D:\datos\endes"           # PowerShell
```

Sin ella se usa `../DATA/DATASET FINAL - DEPRESION SALUD MENTAL`, que es donde están en la
máquina de desarrollo.

### 3. Comprobar que el entorno funciona

```bash
python -m pytest -q            # 154 pruebas; las de verificación contra los .sav se saltan solas
python -m ruff check .
```

Las pruebas del dataset se saltan solas si `datos/final/data.parquet` no existe todavía,
así que sirven como comprobación del entorno antes de construir nada.

### 4. Ejecutar el pipeline

```bash
cp .env.example .env        # rellenar solo si se usa el agente con LLM

make data          # dataset único desde los .sav, con georreferenciación
make analisis      # las catorce etapas del análisis epidemiológico
make boletin       # boletín de 15 secciones en boletin/ y docs/referencias.bib
make notebooks     # genera los nueve notebooks y los ejecuta
make tests         # 154 pruebas: dataset, geografía, agente, API y medidas de asociación
make equivalencia  # réplica en R y comparación con Python
make web           # aplicación interactiva en http://localhost:8000
make agente        # demostración del agente LangGraph
```

Si `make` no está disponible —el caso en Windows sin MSYS—, cada objetivo es una lista de
comandos `python` que se pueden ejecutar directamente; el Makefile sirve entonces como
documentación del orden.

**Los notebooks necesitan el kernel del proyecto.** `make notebooks` lo registra. El kernel
genérico `python3` puede apuntar a otro intérprete de la máquina, sin `svy` ni `lightgbm`,
y entonces tres notebooks fallan con `ModuleNotFoundError` aunque los mismos scripts corran
bien desde la consola.

**La réplica en R** necesita R instalado. Si no está en el PATH:
`make equivalencia RSCRIPT="/ruta/a/Rscript.exe"`.

**Para desplegar** el servicio en Render, la guía paso a paso está en
[`docs/DESPLIEGUE_RENDER.md`](docs/DESPLIEGUE_RENDER.md). El boletín se publica solo al
empujar la rama `gh-pages`.

El dataset se versiona por hash SHA-256 en `datos/final/data_hash.txt`: dos ejecuciones
sobre los mismos insumos producen el mismo hash.

---

## Estructura

```
├── datos/final/data.parquet      ← dataset único; todo el proyecto consume esto
├── codigo/
│   ├── src/depresion/            config · io · limpieza · variables · encuesta
│   │                             epi · supuestos · modelos · viz · geo
│   ├── scripts/                  pipeline y análisis, uno por etapa
│   ├── notebooks/                01…09, narrativos
│   └── R/analisis_equivalente.R  réplica con survey: coincide hasta el 4.º decimal
├── resultados/
│   ├── tablas/                   79 tablas en csv (con xlsx y tex)
│   ├── figuras/                  20 figuras en png (300 dpi) + pdf
│   ├── mapas/                    7 mapas + coroplético interactivo
│   └── modelos/                  coeficientes, joblib y model_card.md
├── boletin/                      boletín de 15 secciones
├── api/                          FastAPI + web/ + render.yaml (sin Docker)
├── agente/                       LangGraph con guardrails y modo degradado
├── docs/                         decisiones, diccionario, DAG, STROBE, grafo
└── tests/                        pytest
```

---

## Los cuatro productos

### 1. Análisis epidemiológico

Cubre medidas de frecuencia con diseño complejo; tabla 2×2 con OR, razón de prevalencias
y chi cuadrado (con la versión de Rao y Scott); medidas de impacto basadas en prevalencia
(diferencia, fracción en expuestos y fracción poblacional); sesgo y confusión por
Mantel-Haenszel; la altitud como posible confusor; ANOVA de un factor con verificación de
supuestos; regresión lineal; y regresión logística. En un estudio transversal no hay incidencia,
así que se reporta razón de prevalencias y no riesgo relativo.

Los supuestos se verifican y **se reportan aunque fallen**. El PHQ-9 tiene asimetría 2,4 y
la mitad de la muestra en cero, así que la regresión lineal cruda viola normalidad y
homocedasticidad: se comparan cuatro tratamientos (crudo, raíz cuadrada, errores robustos
HC3 y alternativa de conteo) y se explica por qué la conclusión sustantiva se apoya en la
logística.

### 2. Boletín HTML

Quince páginas estáticas y autocontenidas, generadas por script desde `resultados/`, con
mapas, modo claro/oscuro y un **explorador de tasas observadas por perfil y un selector por
departamento que funcionan en el navegador**, sin backend. Incluye una sección de medidas de
asociación y riesgo atribuible, otra de validez interna y sesgos, y la lista de referencias en
APA 7 (la misma, en BibTeX, está en [`docs/referencias.bib`](docs/referencias.bib)). Se publica en
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
  temporalidad ni descartar causalidad reversa. Para varios factores (violencia de pareja,
  diabetes, obesidad, tabaco) la literatura de seguimiento encuentra la relación en los dos
  sentidos. Nada aquí debe leerse como efecto causal.
- **Lo ecológico no es individual.** Los mapas y la correlación entre departamentos describen
  grupos; leerlos como riesgo individual es la falacia ecológica.
- **Autorreporte.** El PHQ-9 es tamizaje, no diagnóstico clínico. Las condiciones crónicas
  también son autorreportadas.
- **Sesgo de selección.** Se excluyó al 9,4 % sin PHQ-9 completo (777 ausentes, 899 rechazos, 1 419
  entrevistas incompletas, 70 con discapacidad, 3 otras); no se puede decir hacia dónde mueve la
  prevalencia. El universo son los hogares particulares. Además, el análisis con casos completos deja
  fuera a 1 145 personas que nunca asistieron a la escuela (prevalencia 15,9 %): incluirlas como
  categoría no cambia ningún OR del modelo principal en más de 6,4 %, aunque sí influye en la OR sin
  ajustar de la altitud. Se mantiene el modelo con casos completos como principal y esta comparación como
  sensibilidad (decisión del 2026-11-12 en `docs/decisiones_metodologicas.md`).
- **Confusión residual.** No se mide ingreso, lengua materna, seguro de salud ni distancia a un
  servicio.
- **Región natural derivada** por altitud, no la clasificación oficial por distrito. Ajustar
  por ella al estimar la altitud es controlar por una versión gruesa de la propia exposición: se
  reporta con esa advertencia y se usa el departamento como control más fino.
- **La numeración de los ítems del PHQ-9 en la ENDES no es la canónica.** El ítem de
  pensamientos de hacerse daño es `QS700H`, no `QS700I`: el cuestionario coloca «se sintió
  mal consigo mismo» al final. Cualquier reanálisis que asuma el orden estándar señalará el
  ítem equivocado.
- **Discriminación moderada** (AUC 0,67): sirve para priorizar poblaciones, no para decidir
  sobre personas.
- **Sin totales poblacionales**, por lo dicho sobre el ponderador.
- **Las fracciones atribuibles** se apoyan en prevalencia y solo equivalen a casos evitables si la
  asociación fuera causal y no confundida, cosa que este diseño no permite comprobar.
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

La lista completa, en APA 7, está en la sección 15 del boletín, y en BibTeX en
[`docs/referencias.bib`](docs/referencias.bib). Ambas salen del mismo módulo
(`codigo/scripts/referencias_boletin.py`), que guarda además qué se comprobó de cada una al
abrirla. Las principales:

- Kroenke, K., Spitzer, R. L., & Williams, J. B. W. (2001). The PHQ-9: Validity of a brief
  depression severity measure. *Journal of General Internal Medicine, 16*(9), 606-613.
  <https://doi.org/10.1046/j.1525-1497.2001.016009606.x>
- Basauri-Delgado, M., Mesía-Guevara, J.-A., & Saintila, J. (2025). Influence of
  sociodemographic, socioeconomic, and health factors on depression in the Peruvian population:
  A cross-sectional study. *Journal of Primary Care & Community Health, 16*.
  <https://doi.org/10.1177/21501319251342090>
- Zegarra-Rodríguez, C. A., Plasencia-Dueñas, N. R., & Failoc-Rojas, V. E. (2022). Disparities in
  the prevalence of screened depression at different altitudes in Peru: A retrospective analysis
  of the ENDES 2019. *PLOS ONE, 17*(12), e0278947. <https://doi.org/10.1371/journal.pone.0278947>
- Hernández-Vásquez, A., Vargas-Fernández, R., Rojas-Roque, C., & Gamboa-Unsihuay, J. E. (2022).
  Association between altitude and depression in Peru: An 8-year pooled analysis of
  population-based surveys. *Journal of Affective Disorders, 299*, 536-544.
  <https://doi.org/10.1016/j.jad.2021.12.059>
- Instituto Nacional de Estadística e Informática. (2026). *Ficha técnica: Encuesta Demográfica y
  de Salud Familiar (ENDES) 2025*. <https://proyectos.inei.gob.pe/microdatos/>
- Organización Mundial de la Salud. (2026, 11 de septiembre). *Trastorno depresivo (depresión)*.
  <https://www.who.int/es/news-room/fact-sheets/detail/depression>
- Zou, G. (2004). A modified Poisson regression approach to prospective studies with binary data.
  *American Journal of Epidemiology, 159*(7), 702-706. <https://doi.org/10.1093/aje/kwh090>
- Lumley, T. (2010). *Complex surveys: A guide to analysis using R*. Wiley.
  <https://doi.org/10.1002/9780470580066>

## Licencia

MIT — ver [LICENSE](LICENSE).
