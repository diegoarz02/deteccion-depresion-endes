# ── Etapa 1: dependencias ────────────────────────────────────────────
FROM python:3.12-slim AS dependencias

WORKDIR /instalacion
COPY api/requirements.txt .
RUN pip install --no-cache-dir --prefix=/instalado -r requirements.txt

# ── Etapa 2: imagen final ────────────────────────────────────────────
FROM python:3.12-slim

# Usuario sin privilegios: el servicio no necesita root.
RUN useradd --create-home --shell /bin/bash servicio
WORKDIR /app

COPY --from=dependencias /instalado /usr/local

# Solo lo imprescindible para servir: el código de la API y los coeficientes.
# Los microdatos, los notebooks y los modelos de árboles NO entran en la imagen.
COPY api/ ./api/
COPY resultados/modelos/coeficientes_logistico.json ./resultados/modelos/

USER servicio

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    LOG_LEVEL=INFO

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
