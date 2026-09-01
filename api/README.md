# API de tamizaje epidemiológico de depresión

Expone el modelo logístico del estudio ENDES 2025 como servicio HTTP.

> **Esta API no diagnostica.** Estima riesgo epidemiológico poblacional con fines
> académicos y de salud pública. No reemplaza la evaluación de un profesional de salud
> mental. En el Perú: **Línea 113, opción 5**.

---

## Ejecutar en local

```bash
pip install -r api/requirements.txt
uvicorn api.main:app --reload --port 8000
```

Documentación interactiva en <http://localhost:8000/docs>.

### Con Docker

```bash
docker build -f api/Dockerfile -t api-depresion .
docker run -p 8000:8000 api-depresion
curl http://localhost:8000/health
```

---

## Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| `GET` | `/health` | Estado del servicio y si el modelo está cargado |
| `GET` | `/model-info` | Metadatos del modelo, variables y **usos prohibidos** |
| `GET` | `/metrics` | Métricas de rendimiento tal como se reportan en el informe |
| `POST` | `/predict` | Riesgo estimado de un perfil |
| `POST` | `/predict/batch` | Hasta 500 perfiles en una llamada |
| `POST` | `/interpretar` | Interpretación en lenguaje natural vía el agente LangGraph |

---

## Ejemplos

### Estado

```bash
curl http://localhost:8000/health
```

```json
{"estado":"ok","modelo_cargado":true,"version":"1.0.0"}
```

### Predicción

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "sexo": "Mujer",
    "grupo_etario": "60+",
    "nivel_educativo": "Primaria o menos",
    "region_natural": "Sierra",
    "area": "Rural",
    "edad": 68,
    "hipertension": true,
    "diabetes": true
  }'
```

```json
{
  "probabilidad": 0.19952,
  "probabilidad_pct": 19.95,
  "categoria_riesgo": "alto",
  "prevalencia_nacional": 0.06213,
  "razon_sobre_prevalencia": 3.21,
  "factores_contribuyentes": [
    {"factor": "Sexo femenino", "contribucion_log_odds": 1.0776, "odds_ratio": 2.938},
    {"factor": "Grupo etario: 60+", "contribucion_log_odds": 0.5115, "odds_ratio": 1.668},
    {"factor": "Nivel educativo: Primaria o menos", "contribucion_log_odds": 0.3943, "odds_ratio": 1.483}
  ],
  "disclaimer": "Esta herramienta estima riesgo epidemiológico…",
  "linea_ayuda": "Si te sientes mal, busca ayuda profesional…"
}
```

**Cómo leerlo:** de cada cien personas con este perfil en el Perú, unas 20 presentarían
sintomatología depresiva moderada o grave. Es 3,2 veces la prevalencia nacional. **No
significa que la persona que consulta tenga depresión.**

### Lote

```bash
curl -X POST http://localhost:8000/predict/batch \
  -H "Content-Type: application/json" \
  -d '{"perfiles":[
    {"sexo":"Hombre","grupo_etario":"30-39","nivel_educativo":"Superior","region_natural":"Costa","area":"Urbano","edad":35},
    {"sexo":"Mujer","grupo_etario":"20-29","nivel_educativo":"Secundaria","region_natural":"Selva","area":"Rural","edad":25}
  ]}'
```

### Interpretación con el agente

```bash
curl -X POST http://localhost:8000/interpretar \
  -H "Content-Type: application/json" \
  -d '{"sexo":"Mujer","grupo_etario":"50-59","nivel_educativo":"Secundaria","region_natural":"Sierra","area":"Rural","edad":55,"hipertension":true}'
```

Funciona **con o sin** clave de API: si no hay `ANTHROPIC_API_KEY`, el agente responde
con plantillas deterministas construidas sobre las mismas cifras.

### Metadatos

```bash
curl http://localhost:8000/model-info | python -m json.tool
```

---

## Validación

Pydantic v2 con `extra="forbid"`: cualquier campo no declarado se rechaza, para que un
error de tipeo no pase inadvertido.

| Regla | Respuesta |
|---|---|
| Edad fuera de 15-97 | `422` |
| Edad incoherente con el grupo etario | `422` con el mensaje explicando el rango |
| Categoría inexistente | `422` con las opciones válidas |
| Campo no declarado | `422` |
| Más de 500 perfiles en un lote | `422` |
| Más de 60 peticiones por minuto | `429` con `reintentar_en_segundos` |

---

## Decisión de arquitectura: solo la logística

**Se despliega únicamente el modelo de regresión logística.** No XGBoost, no SHAP, no
pandas.

El plan gratuito de Render ofrece unos 512 MB de RAM. Cargar `pandas` + `xgboost` +
`shap` consume buena parte de ese presupuesto solo en importar, y el servicio se cae
bajo carga. Frente a eso:

- El modelo logístico son **17 coeficientes en un JSON**. El servicio arranca al
  instante y consume decenas de megabytes.
- Es además **el modelo del informe**: el que tiene intervalos de confianza, diagnóstico
  de supuestos y una interpretación epidemiológica defendible.
- Los modelos de árboles se quedan en el análisis local, y los valores SHAP que muestra
  el boletín están **precalculados** y servidos como datos estáticos.

No es una limitación tapada: es la elección correcta incluso con más memoria disponible,
porque el modelo que se publica debe ser el que se puede explicar.

### Sobre el arranque en frío

En el plan gratuito de Render el servicio se suspende tras un rato sin tráfico. La
primera petición tras la suspensión puede tardar **unos 50 segundos**. Las siguientes
responden con normalidad. Si eso importa para una demostración, conviene despertar el
servicio con un `GET /health` un minuto antes.

---

## Despliegue en Render

1. Sube el repositorio a GitHub.
2. En Render: **New → Blueprint**, apunta a `api/render.yaml`.
3. Render construye la imagen con `api/Dockerfile` y publica el servicio.
4. Ajusta `CORS_ORIGINS` al dominio donde esté el boletín.
5. Comprueba `GET /health` antes de dar el despliegue por bueno.

`autoDeploy` está en `false` a propósito: el despliegue se dispara a mano, para que un
commit de análisis no reemplace la API sin querer.

**Ninguna clave se escribe en `render.yaml`.** Las variables sensibles se configuran en
el panel de Render.

---

## Tests

```bash
python -m pytest api/tests/ -v
```

14 tests que cubren estado, predicción, validación, lotes y el agente. Uno de ellos
comprueba que **un perfil con más factores de riesgo puntúa más alto**: es la forma más
directa de detectar un modelo invertido, que es el fallo más silencioso posible en un
servicio de predicción.

## Despliegue

> **`render.yaml` vive en la raíz del repositorio, no aquí.** Render solo detecta un
> Blueprint de forma automática si el archivo se llama `render.yaml` y está arriba del
> todo. `rootDir: .` ya apuntaba a la raíz, así que el contenido no cambió al moverlo.

Render con **runtime nativo de Python**, sin Docker. El despliegue es manual
(`autoDeploy: false`): un push no debe publicar
sin revisar antes.

El `Dockerfile` se retiró en la tercera corrida. No aportaba nada: la API no necesita
ninguna dependencia que no venga en una rueda de PyPI —carga el modelo desde un JSON de
coeficientes, no desde un `.joblib`, así que ni scikit-learn ni pandas entran en
producción— y una imagen solo añadía minutos de construcción y una capa más que mantener.

### Antes de desplegar

1. `ANTHROPIC_API_KEY` se pone **en el panel de Render**, nunca en el repositorio. Sin
   ella el agente responde igual, con plantillas deterministas sobre las cifras reales.
2. `CORS_ORIGINS` debe incluir el dominio de GitHub Pages donde vive el boletín. La
   aplicación web no lo necesita: la sirve este mismo proceso, desde el mismo origen.
3. Comprobar que `api/datos/` está poblado: `coeficientes.json`, `contexto.json`,
   `departamentos.geojson` y `tasas_observadas.json`. Los generan
   `preparar_datos_web.py` y `preparar_tasas_observadas.py`, y sin ellos el servicio
   arranca pero responde 404 en el contexto y en la tasa observada.

### Después de desplegar

- `/health` responde 200 con `modelo_cargado: true`.
- El flujo completo de la aplicación, incluido el panel de límites.
- El agente con y sin clave: las dos rutas deben dar respuesta.
- El nodo de crisis, con un perfil de prueba que lleve `item_autolesion` ≥ 1.
- Consumo de memoria por debajo de 512 MB.
