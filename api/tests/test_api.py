"""Tests de la API con TestClient.

Ejecutar desde la raíz del proyecto::

    python -m pytest api/tests/ -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

API = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API))

from main import app  # noqa: E402

PERFIL_BASE = {
    "sexo": "Hombre", "grupo_etario": "30-39", "nivel_educativo": "Superior",
    "region_natural": "Costa", "area": "Urbano", "edad": 35,
}


@pytest.fixture(scope="module")
def cliente():
    """Cliente de pruebas con el lifespan ejecutado."""
    with TestClient(app) as c:
        yield c


# ── Estado ────────────────────────────────────────────────────────────


def test_health(cliente):
    """El endpoint de salud responde y declara si el modelo está cargado."""
    r = cliente.get("/health")
    assert r.status_code == 200
    assert r.json()["estado"] in ("ok", "degradado")


def test_model_info(cliente):
    """Los metadatos incluyen los usos prohibidos, no solo las métricas."""
    r = cliente.get("/model-info")
    assert r.status_code == 200
    d = r.json()
    assert d["instrumento"] == "PHQ-9"
    assert d["punto_de_corte"] == 10
    assert len(d["usos_prohibidos"]) >= 3
    assert "diagnóstico" in d["disclaimer"].lower()


def test_metrics(cliente):
    """Las métricas se exponen con su nota de interpretación."""
    r = cliente.get("/metrics")
    assert r.status_code == 200
    assert 0.5 < r.json()["auc_roc"] < 1.0


# ── Predicción ────────────────────────────────────────────────────────


def test_predict_devuelve_probabilidad_valida(cliente):
    """La predicción está en [0, 1] y trae el disclaimer."""
    r = cliente.post("/predict", json=PERFIL_BASE)
    assert r.status_code == 200
    d = r.json()
    assert 0 <= d["probabilidad"] <= 1
    assert d["categoria_riesgo"] in ("bajo", "medio", "alto")
    assert "no constituye un diagnóstico" in d["disclaimer"].lower()
    assert "113" in d["linea_ayuda"]


def test_perfil_de_mayor_riesgo_da_mayor_probabilidad(cliente):
    """Un perfil con más factores de riesgo debe puntuar más alto.

    Es la comprobación de que el modelo no está invertido, que es el error más
    silencioso que puede tener un servicio de predicción.
    """
    bajo = cliente.post("/predict", json=PERFIL_BASE).json()
    alto = cliente.post("/predict", json={
        **PERFIL_BASE, "sexo": "Mujer", "grupo_etario": "60+", "edad": 70,
        "nivel_educativo": "Primaria o menos", "region_natural": "Sierra",
        "consumo_problematico_alcohol": True, "hipertension": True, "diabetes": True,
    }).json()
    assert alto["probabilidad"] > bajo["probabilidad"]
    assert alto["razon_sobre_prevalencia"] > bajo["razon_sobre_prevalencia"]


def test_factores_contribuyentes(cliente):
    """Se devuelven como mucho tres factores, todos con OR mayor que 1."""
    r = cliente.post("/predict", json={
        **PERFIL_BASE, "sexo": "Mujer", "consumo_problematico_alcohol": True,
        "hipertension": True})
    factores = r.json()["factores_contribuyentes"]
    assert len(factores) <= 3
    assert all(f["odds_ratio"] > 1 for f in factores)


# ── Validación ────────────────────────────────────────────────────────


def test_edad_fuera_de_rango(cliente):
    """Una edad menor de 15 se rechaza: la encuesta no cubre esa población."""
    r = cliente.post("/predict", json={**PERFIL_BASE, "grupo_etario": "15-19", "edad": 12})
    assert r.status_code == 422


def test_edad_incoherente_con_grupo_etario(cliente):
    """Se rechaza una edad que no corresponde al grupo declarado."""
    r = cliente.post("/predict", json={**PERFIL_BASE, "grupo_etario": "60+", "edad": 30})
    assert r.status_code == 422
    assert "grupo etario" in r.text.lower()


def test_categoria_invalida(cliente):
    """Una categoría inexistente se rechaza con un error claro."""
    r = cliente.post("/predict", json={**PERFIL_BASE, "region_natural": "Antártida"})
    assert r.status_code == 422


def test_campo_extra_rechazado(cliente):
    """Los campos no declarados se rechazan: evita errores de tipeo silenciosos."""
    r = cliente.post("/predict", json={**PERFIL_BASE, "campo_inventado": 1})
    assert r.status_code == 422


def test_campo_faltante(cliente):
    """Falta un campo obligatorio."""
    incompleto = {k: v for k, v in PERFIL_BASE.items() if k != "sexo"}
    assert cliente.post("/predict", json=incompleto).status_code == 422


# ── Lotes ─────────────────────────────────────────────────────────────


def test_batch(cliente):
    """El lote devuelve tantas predicciones como perfiles."""
    r = cliente.post("/predict/batch", json={"perfiles": [PERFIL_BASE, PERFIL_BASE]})
    assert r.status_code == 200
    assert r.json()["n"] == 2


def test_batch_vacio_rechazado(cliente):
    """Un lote sin perfiles es un error de la petición."""
    assert cliente.post("/predict/batch", json={"perfiles": []}).status_code == 422


# ── Agente ────────────────────────────────────────────────────────────


def test_interpretar_siempre_responde(cliente):
    """La interpretación funciona con o sin LLM, y nunca diagnostica."""
    r = cliente.post("/interpretar", json=PERFIL_BASE)
    assert r.status_code == 200
    d = r.json()
    assert d["modo"] in ("llm", "degradado")
    assert len(d["texto"]) > 60
    prohibidas = ["usted tiene depresión", "usted padece", "le diagnostico",
                  "debe tomar", "recete", "su diagnóstico es"]
    texto = d["texto"].lower()
    assert not any(f in texto for f in prohibidas), f"Lenguaje diagnóstico: {d['texto']}"
    assert "113" in d["texto"]
