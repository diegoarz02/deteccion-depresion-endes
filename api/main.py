"""API de tamizaje epidemiológico de depresión (ENDES 2025).

Expone el modelo logístico del estudio como servicio. El modelo se carga una
sola vez en el *lifespan*, no en cada petición.

Uso local
---------
    uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).resolve().parent))

from esquemas import (  # noqa: E402
    DISCLAIMER,
    InfoModelo,
    LoteEntrada,
    LoteSalida,
    Perfil,
    Prediccion,
    Salud,
)
from servicio import RUTA_DATOS, ModeloNoDisponible, servicio  # noqa: E402

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("api")

VERSION = "1.0.0"

ORIGENES = [o.strip() for o in os.getenv(
    "CORS_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000,https://diegoarz02.github.io"
).split(",") if o.strip()]


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Carga el modelo al arrancar y lo libera al apagar."""
    try:
        servicio.cargar()
        log.info("Modelo cargado correctamente")
    except ModeloNoDisponible as e:
        log.error("No se pudo cargar el modelo: %s", e)
    yield
    log.info("Apagando el servicio")


app = FastAPI(
    title="API de tamizaje epidemiológico de depresión",
    description=(
        "Estima el riesgo epidemiológico de sintomatología depresiva moderada o grave "
        "(PHQ-9 ≥ 10) en población peruana de 15 años a más, a partir del modelo "
        f"logístico ajustado sobre la ENDES 2025.\n\n**{DISCLAIMER}**"
    ),
    version=VERSION,
    lifespan=ciclo_de_vida,
    contact={"name": "Diego Alonso Araujo Villegas — UNMSM"},
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Limitación de tasa sencilla, en memoria ───────────────────────────
_PETICIONES: dict[str, list[float]] = {}
LIMITE_POR_MINUTO = int(os.getenv("RATE_LIMIT", "60"))


@app.middleware("http")
async def limitar_tasa(request: Request, call_next):
    """Limita las peticiones por IP y minuto.

    Implementación en memoria, suficiente para una sola instancia. Con varias
    réplicas haría falta un almacén compartido.
    """
    if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
        return await call_next(request)
    ip = request.client.host if request.client else "desconocida"
    ahora = time.time()
    ventana = _PETICIONES.setdefault(ip, [])
    ventana[:] = [t for t in ventana if ahora - t < 60]
    if len(ventana) >= LIMITE_POR_MINUTO:
        return JSONResponse(
            status_code=429,
            content={"detalle": f"Límite de {LIMITE_POR_MINUTO} peticiones por minuto superado.",
                     "reintentar_en_segundos": int(60 - (ahora - ventana[0]))})
    ventana.append(ahora)
    return await call_next(request)


@app.exception_handler(ModeloNoDisponible)
async def modelo_no_disponible(request: Request, exc: ModeloNoDisponible):
    """Devuelve 503 cuando el modelo no está cargado."""
    return JSONResponse(status_code=503,
                        content={"detalle": "El modelo no está disponible.", "causa": str(exc)})


# ── Endpoints ─────────────────────────────────────────────────────────


@app.get("/health", response_model=Salud, tags=["Estado"])
async def salud() -> Salud:
    """Comprueba que el servicio responde y si el modelo está cargado."""
    return Salud(estado="ok" if servicio.cargado else "degradado",
                 modelo_cargado=servicio.cargado, version=VERSION)


@app.get("/model-info", response_model=InfoModelo, tags=["Estado"])
async def info_modelo() -> InfoModelo:
    """Devuelve los metadatos del modelo desplegado y sus usos prohibidos."""
    if not servicio.cargado:
        raise ModeloNoDisponible("El modelo no está cargado")
    return InfoModelo(**servicio.info())


@app.post("/predict", response_model=Prediccion, tags=["Predicción"])
async def predecir(perfil: Perfil) -> Prediccion:
    """Estima el riesgo epidemiológico de un perfil.

    La probabilidad se interpreta **poblacionalmente**: cuántas personas con
    este perfil, de cada cien, presentarían sintomatología depresiva moderada o
    grave. No es un diagnóstico de la persona que consulta.
    """
    return servicio.predecir(perfil)


@app.post("/predict/batch", response_model=LoteSalida, tags=["Predicción"])
async def predecir_lote(lote: LoteEntrada) -> LoteSalida:
    """Estima el riesgo de hasta 500 perfiles en una sola llamada."""
    preds = [servicio.predecir(p) for p in lote.perfiles]
    return LoteSalida(n=len(preds), predicciones=preds)


@app.get("/metrics", tags=["Estado"])
async def metricas() -> dict:
    """Métricas de rendimiento del modelo, tal como se reportan en el informe."""
    if not servicio.cargado:
        raise ModeloNoDisponible("El modelo no está cargado")
    m = servicio.metadatos
    return {
        "auc_roc": m.get("auc"),
        "brier_score": m.get("brier"),
        "prevalencia_nacional": m.get("prevalencia"),
        "n_entrenamiento": m.get("n"),
        "nota": ("La discriminación es moderada por diseño: el modelo sirve para "
                 "priorizar poblaciones, no para decidir sobre una persona."),
    }


@app.post("/interpretar", tags=["Agente"])
async def interpretar(perfil: Perfil) -> dict:
    """Genera una interpretación en lenguaje natural mediante el agente.

    Si no hay clave de API configurada o el proveedor falla, el agente responde
    igual, con plantillas deterministas construidas sobre las cifras reales del
    modelo. El servicio nunca depende de que haya un LLM disponible.
    """
    prediccion = servicio.predecir(perfil)
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from agente.grafo import interpretar_perfil

        resultado = interpretar_perfil(perfil.model_dump(mode="json"),
                                       prediccion.model_dump(mode="json"))
        return resultado
    except Exception as e:  # el agente nunca debe tumbar la API
        log.warning("El agente falló, se responde en modo degradado: %s", e)
        return {
            "texto": (
                f"Un perfil como el descrito presenta una probabilidad estimada del "
                f"{prediccion.probabilidad_pct:.1f} % de sintomatología depresiva moderada "
                f"o grave, frente al {prediccion.prevalencia_nacional * 100:.1f} % de la "
                f"población peruana de 15 años a más. "
                f"{prediccion.disclaimer} {prediccion.linea_ayuda}"),
            "modo": "degradado",
            "prediccion": prediccion.model_dump(mode="json"),
            "trazas": [{"nodo": "respaldo_api", "detalle": str(e)[:200]}],
        }


@app.get("/contexto-departamento/{codigo}", tags=["Contexto"])
async def contexto_departamento(codigo: str) -> dict:
    """Devuelve la prevalencia y la brecha de atención de un departamento."""
    d = servicio.departamento(codigo)
    if d is None:
        return JSONResponse(status_code=404,
                            content={"detalle": f"No existe el departamento {codigo}."})
    nacional = servicio.contexto().get("nacional", {})
    return {"departamento": d, "nacional": nacional,
            "razon_sobre_nacional": (round(d["prevalencia"] / nacional["prevalencia"], 2)
                                     if nacional.get("prevalencia") else None)}


@app.get("/mapa-datos", tags=["Contexto"])
async def mapa_datos() -> dict:
    """Datos de los 25 departamentos para dibujar el mapa en el navegador."""
    c = servicio.contexto()
    return {"nacional": c.get("nacional", {}), "departamentos": c.get("departamentos", []),
            "fuente": c.get("fuente", "ENDES 2025 (INEI)")}


@app.get("/geojson", tags=["Contexto"], include_in_schema=False)
async def geojson():
    """Sirve el GeoJSON simplificado de los departamentos."""
    ruta = RUTA_DATOS / "departamentos.geojson"
    if not ruta.exists():
        return JSONResponse(status_code=404, content={"detalle": "GeoJSON no disponible."})
    return FileResponse(ruta, media_type="application/geo+json")


@app.get("/api", tags=["Estado"], include_in_schema=False)
async def raiz_api() -> dict:
    """Punto de entrada de la API con los enlaces útiles."""
    return {
        "servicio": "API de tamizaje epidemiológico de depresión (ENDES 2025)",
        "version": VERSION,
        "documentacion": "/docs",
        "estado": "/health",
        "disclaimer": DISCLAIMER,
    }


# ── Interfaz web ──────────────────────────────────────────────────────
# Se sirve desde el mismo proceso que la API: un solo servicio en Render, un
# solo arranque en frío, y sin problemas de CORS entre el navegador y el
# backend.
RUTA_WEB = Path(__file__).resolve().parent / "web"
if RUTA_WEB.exists():
    app.mount("/estatico", StaticFiles(directory=RUTA_WEB), name="estatico")

    @app.get("/", include_in_schema=False)
    async def inicio():
        """Sirve la aplicación interactiva."""
        return FileResponse(RUTA_WEB / "index.html")
else:
    @app.get("/", include_in_schema=False)
    async def inicio() -> dict:
        """Sin interfaz web disponible: se responde con los metadatos."""
        return {"servicio": "API de tamizaje de depresión (ENDES 2025)",
                "documentacion": "/docs", "disclaimer": DISCLAIMER}
