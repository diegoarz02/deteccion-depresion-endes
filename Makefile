.PHONY: ayuda data analisis boletin notebooks tests calidad equivalencia datos-web api web agente todo limpiar

# Ruta de Rscript en Windows. Se puede sobrescribir:  make equivalencia RSCRIPT=Rscript
RSCRIPT ?= C:/Program Files/R/R-4.4.3/bin/Rscript.exe

ayuda:
	@echo "make data          - construye datos/final/data.parquet (incluye georreferenciacion)"
	@echo "make analisis      - ejecuta las diez etapas del analisis epidemiologico"
	@echo "make boletin       - genera el boletin de 13 secciones en boletin/"
	@echo "make notebooks     - genera los nueve notebooks y los ejecuta"
	@echo "make tests         - pytest de datos, geo, agente y API"
	@echo "make calidad       - ruff"
	@echo "make equivalencia  - replica en R y la compara con Python"
	@echo "make datos-web     - precalcula el JSON estatico que consume la app"
	@echo "make web           - app interactiva en http://localhost:8000"
	@echo "make agente        - demostracion del agente LangGraph"
	@echo "make todo          - data + analisis + datos-web + boletin + tests"
	@echo "make limpiar       - borra caches de Python"

data:
	python codigo/scripts/construir_dataset.py
	python codigo/scripts/figura_strobe.py

analisis:
	python codigo/scripts/analisis_01_screening.py
	python codigo/scripts/analisis_02_descriptivo.py
	python codigo/scripts/analisis_03_asociacion.py
	python codigo/scripts/analisis_04_anova_lineal.py
	python codigo/scripts/analisis_05_logistica.py
	python codigo/scripts/analisis_06_ml.py
	python codigo/scripts/analisis_07_altitud.py
	python codigo/scripts/analisis_08_mediacion.py
	python codigo/scripts/analisis_09_mapas.py
	python codigo/scripts/analisis_10_deff.py

boletin:
	python codigo/scripts/preparar_recursos_boletin.py
	python codigo/scripts/generar_boletin.py
	@echo "Sirve con: python -m http.server 8000 --directory boletin"

# Los notebooks se ejecutan con el kernel del proyecto, no con "python3": ese
# apunta a otro interprete de la maquina y no tiene svy ni lightgbm instalados.
notebooks:
	python codigo/scripts/generar_notebooks.py
	python -m ipykernel install --user --name depresion-endes \
		--display-name "Python (depresión ENDES)"
	python -m jupyter nbconvert --to notebook --execute \
		--ExecutePreprocessor.kernel_name=depresion-endes \
		--ExecutePreprocessor.timeout=3600 \
		--output-dir resultados/notebooks_ejecutados codigo/notebooks/*.ipynb

# Sin ruta: pytest toma testpaths de pyproject.toml, que incluye tests/ y
# api/tests/. Pasar solo `tests/` se saltaba catorce pruebas de la API.
tests:
	python -m pytest -q

calidad:
	python -m ruff check .

# Doble implementacion: si survey (R) y svy (Python) no coinciden, uno de los
# dos declara mal el diseno muestral. El script falla con codigo 1 si difieren.
equivalencia:
	"$(RSCRIPT)" codigo/R/analisis_equivalente.R > resultados/tablas/replica_R.txt 2>&1
	python codigo/scripts/verificar_equivalencia_R.py

# El GeoJSON de la web lo exporta analisis_09_mapas.py; este paso solo deja
# escrito el contexto departamental para que la API no necesite pandas.
datos-web:
	python codigo/scripts/preparar_datos_web.py

api web: datos-web
	python -m uvicorn api.main:app --reload --port 8000

agente:
	python agente/grafo.py

todo: data analisis datos-web boletin tests

limpiar:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
