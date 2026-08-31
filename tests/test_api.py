"""Tests de la API y de la aplicación web.

El riesgo que vigilan no es que la API se caiga, sino que **acepte** lo que no
debe: un perfil con el puntaje PHQ-9 dentro, que es el desenlace y convertiría
la predicción en una tautología, o un contrato que cambie sin que nadie lo note.

Ejecutar con::

    pytest tests/test_api.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "api"))

fastapi_testclient = pytest.importorskip("fastapi.testclient")

from pydantic import ValidationError  # noqa: E402

from esquemas import Perfil  # noqa: E402


@pytest.fixture(scope="module")
def cliente():
    """Levanta la aplicación una sola vez para todos los tests."""
    from main import app

    with fastapi_testclient.TestClient(app) as c:
        yield c


PERFIL_BASE = {
    "sexo": "Mujer", "grupo_etario": "60+", "edad": 68,
    "nivel_educativo": "Primaria o menos", "region_natural": "Sierra",
    "area": "Rural", "hipertension": True, "diabetes": True,
}


# ─────────────────────────────────────────────────────────────────────
# Contrato de entrada
# ─────────────────────────────────────────────────────────────────────


def test_el_esquema_rechaza_campos_desconocidos():
    """Un campo mal escrito debe fallar, no ignorarse en silencio.

    Sin esto, ``area_residencia`` en lugar de ``area`` daría una predicción con
    el valor por defecto y nadie se enteraría.
    """
    with pytest.raises(ValidationError):
        Perfil(**{**PERFIL_BASE, "campo_inventado": 1})


def test_la_edad_debe_ser_coherente_con_el_grupo_etario():
    """Declarar 68 años y grupo «15-19» es un error del que llama, no un dato."""
    with pytest.raises(ValidationError):
        Perfil(**{**PERFIL_BASE, "grupo_etario": "15-19"})


@pytest.mark.parametrize("edad", [14, 98, -1])
def test_la_edad_fuera_del_marco_muestral_se_rechaza(edad):
    """La ENDES entrevista de 15 años a más: fuera de ahí el modelo no aplica."""
    with pytest.raises(ValidationError):
        Perfil(**{**PERFIL_BASE, "edad": edad})


# ─────────────────────────────────────────────────────────────────────
# Que el desenlace no entre como predictor
# ─────────────────────────────────────────────────────────────────────


def test_el_puntaje_phq9_no_altera_la_prediccion(cliente):
    """``phq9_score`` viaja para detectar crisis, no para predecir.

    Si moviera la probabilidad, el modelo estaría prediciendo el desenlace con
    el desenlace. El mismo perfil con y sin puntaje debe dar lo mismo.
    """
    sin = cliente.post("/predict", json=PERFIL_BASE).json()
    con = cliente.post("/predict", json={**PERFIL_BASE, "phq9_score": 27}).json()
    assert sin["probabilidad_pct"] == pytest.approx(con["probabilidad_pct"])


def test_el_item_de_autolesion_tampoco_altera_la_prediccion(cliente):
    """Mismo argumento: es una señal de seguridad, no una covariable."""
    sin = cliente.post("/predict", json=PERFIL_BASE).json()
    con = cliente.post("/predict", json={**PERFIL_BASE, "item_autolesion": 3}).json()
    assert sin["probabilidad_pct"] == pytest.approx(con["probabilidad_pct"])


def test_el_item_de_autolesion_si_cambia_la_interpretacion(cliente):
    """Lo que sí debe hacer: desviar la respuesta al camino de crisis."""
    r = cliente.post("/interpretar", json={**PERFIL_BASE, "item_autolesion": 2}).json()
    assert r["modo"] == "crisis"


# ─────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────


def test_health_responde(cliente):
    """El endpoint que mira Render para saber si el servicio vive."""
    r = cliente.get("/health")
    assert r.status_code == 200
    assert r.json()["estado"] in ("ok", "degradado")


def test_la_prediccion_trae_siempre_el_descargo(cliente):
    """Ninguna respuesta puede salir sin decir que no es un diagnóstico."""
    d = cliente.post("/predict", json=PERFIL_BASE).json()
    assert "diagnóstico" in d["disclaimer"].lower()
    assert d["linea_ayuda"].strip()


def test_la_probabilidad_esta_en_rango(cliente):
    """Una probabilidad fuera de [0, 100] indicaría un modelo mal cargado."""
    d = cliente.post("/predict", json=PERFIL_BASE).json()
    assert 0 <= d["probabilidad_pct"] <= 100


def test_el_contexto_departamental_es_coherente(cliente):
    """La prevalencia de un departamento debe caer dentro de su propio IC."""
    d = cliente.get("/contexto-departamento/21").json()["departamento"]
    assert d["ic_inf"] <= d["prevalencia"] <= d["ic_sup"]
    assert d["n"] > 0


def test_un_departamento_inexistente_da_404(cliente):
    """Mejor un 404 explícito que un cuerpo vacío con 200."""
    assert cliente.get("/contexto-departamento/99").status_code == 404


def test_el_mapa_trae_los_25_departamentos(cliente):
    """25 unidades: 24 departamentos más la Provincia Constitucional del Callao."""
    d = cliente.get("/mapa-datos").json()
    assert len(d["departamentos"]) == 25


def test_cada_departamento_del_mapa_tiene_geometria(cliente):
    """Un código sin polígono dejaría un hueco mudo en el mapa."""
    codigos_datos = {d["codigo"] for d in cliente.get("/mapa-datos").json()["departamentos"]}
    g = cliente.get("/geojson").json()
    codigos_geo = {f["properties"].get("codigo") for f in g["features"]}
    assert codigos_datos <= codigos_geo


def test_la_interfaz_web_se_sirve(cliente):
    """La raíz debe entregar la aplicación, no el JSON de la API."""
    r = cliente.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_el_lote_respeta_su_tope(cliente):
    """501 perfiles deben rechazarse antes de tocar el modelo."""
    r = cliente.post("/predict/batch", json={"perfiles": [PERFIL_BASE] * 501})
    assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────
# El reencuadre: la tasa observada manda sobre la estimación
# ─────────────────────────────────────────────────────────────────────


def test_la_tasa_observada_esta_disponible(cliente):
    """El número protagonista de la aplicación tiene que existir."""
    r = cliente.post("/tasa-observada", json=PERFIL_BASE)
    assert r.status_code == 200
    d = r.json()
    assert d["ic_inf"] <= d["prevalencia"] <= d["ic_sup"]
    assert d["n"] >= 100
    assert d["eventos"] >= 20


def test_la_tasa_observada_declara_que_la_define(cliente):
    """Sin decir a qué se parece el perfil, «parecido» no significa nada."""
    d = cliente.post("/tasa-observada", json=PERFIL_BASE).json()
    assert d["definido_por"].strip()
    assert 1 <= d["nivel"] <= 5


def test_la_tasa_observada_no_es_la_prediccion(cliente):
    """Son dos cantidades distintas y no deben confundirse.

    La tasa observada es un recuento sobre la muestra; la predicción es una
    salida del modelo que incorpora además conductas y condiciones clínicas.
    Que coincidieran exactamente sería señal de que una se calculó con la otra.
    """
    obs = cliente.post("/tasa-observada", json=PERFIL_BASE).json()
    pred = cliente.post("/predict", json=PERFIL_BASE).json()
    assert obs["prevalencia"] != pytest.approx(pred["probabilidad_pct"])


def test_toda_celda_publicada_supera_el_minimo_de_casos():
    """Ninguna cifra del catálogo puede apoyarse en un puñado de personas."""
    import json

    ruta = RAIZ / "api" / "datos" / "tasas_observadas.json"
    catalogo = json.loads(ruta.read_text(encoding="utf-8"))["tasas"]
    assert catalogo, "el catálogo de tasas observadas está vacío"
    for clave, t in catalogo.items():
        assert t["n"] >= 100, clave
        assert t["eventos"] >= 20, clave
        assert t["ic_inf"] <= t["prevalencia"] <= t["ic_sup"], clave


def test_las_celdas_imprecisas_estan_marcadas():
    """El criterio es marcar, no suprimir: la marca tiene que estar puesta."""
    import json

    ruta = RAIZ / "api" / "datos" / "tasas_observadas.json"
    catalogo = json.loads(ruta.read_text(encoding="utf-8"))["tasas"]
    for clave, t in catalogo.items():
        assert t["impreciso"] == (t["cv"] > 0.20), clave
