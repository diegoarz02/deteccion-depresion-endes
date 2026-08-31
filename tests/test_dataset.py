"""Tests de aceptación del dataset analítico (Fase 1).

Ejecutar con::

    pytest tests/ -v

Estos tests son la red de seguridad del pipeline: si alguno falla, el dataset
no debe usarse para analizar.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "codigo" / "src"))

from depresion import config as cfg  # noqa: E402


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    """Carga el dataset final una sola vez para todos los tests."""
    if not cfg.DATASET_FINAL.exists():
        pytest.skip("data.parquet no existe: ejecuta construir_dataset.py primero")
    return pd.read_parquet(cfg.DATASET_FINAL)


# ─────────────────────────────────────────────────────────────────────
# Integridad estructural
# ─────────────────────────────────────────────────────────────────────


def test_sin_duplicados(df):
    """Cada fila es una persona distinta dentro de su hogar."""
    assert not df.duplicated(subset=[cfg.LLAVE, "QSNUMERO"]).any()


def test_ninguna_variable_totalmente_vacia(df):
    """Ninguna variable construida puede tener el 100 % de faltantes."""
    vacias = [c for c in df.columns if df[c].isna().all()]
    assert not vacias, f"Variables totalmente vacías: {vacias}"


def test_filas_esperadas(df):
    """El dataset conserva las 33 569 personas de CSALUD01."""
    assert len(df) == 33_569


# ─────────────────────────────────────────────────────────────────────
# Desenlace
# ─────────────────────────────────────────────────────────────────────


def test_phq9_en_rango(df):
    """El puntaje PHQ-9 vive en [0, 27]: 9 ítems de 0 a 3."""
    s = df.phq9_score.dropna()
    assert s.min() >= 0
    assert s.max() <= 27


def test_phq9_solo_con_nueve_items(df):
    """El puntaje solo existe donde están los nueve ítems."""
    completo = df[cfg.ITEMS_PHQ9].notna().all(axis=1)
    assert (df.phq9_score.notna() == completo).all()
    assert int(completo.sum()) == 30_401


def test_depresion_bin_es_binaria(df):
    """El desenlace principal solo toma los valores 0 y 1."""
    assert set(df.depresion_bin.dropna().unique()) <= {0.0, 1.0}


def test_corte_phq9_coherente(df):
    """depresion_bin es exactamente phq9_score >= 10."""
    s = df.dropna(subset=["phq9_score"])
    assert (s.depresion_bin == (s.phq9_score >= cfg.CORTE_DEPRESION)).all()


def test_prevalencia_conocida(df):
    """La prevalencia cruda de depresión moderada o más es 6,67 %."""
    prev = df.depresion_bin.mean()
    assert prev == pytest.approx(0.0667, abs=0.0005)
    assert int(df.depresion_bin.sum()) == 2_029


# ─────────────────────────────────────────────────────────────────────
# Diseño muestral
# ─────────────────────────────────────────────────────────────────────


def test_suma_de_pesos(df):
    """La suma de pesos escalados es ~36 173.

    Nota: NO es la población peruana de 15+ (~26 millones). El ponderador de
    ENDES es relativo y normalizado, no un factor de expansión. Un test que
    esperase el total poblacional fallaría, y con razón.
    """
    assert df.peso.sum() == pytest.approx(cfg.SUMA_PESOS_ESPERADA, rel=1e-4)
    assert not cfg.PESO_ES_FACTOR_EXPANSION


def test_conglomerados_y_estratos(df):
    """El diseño trae 3 252 conglomerados y 240 estratos."""
    assert df.conglomerado.nunique() == 3_252
    assert df.estrato.nunique() == 240


def test_conglomerados_anidados_en_estratos(df):
    """Cada conglomerado pertenece a un único estrato (nest = TRUE)."""
    por_cong = df.dropna(subset=["estrato"]).groupby("conglomerado").estrato.nunique()
    assert (por_cong == 1).all()


def test_peso_positivo(df):
    """Ningún peso puede ser cero o negativo."""
    assert (df.peso.dropna() > 0).all()


# ─────────────────────────────────────────────────────────────────────
# Trampas verificadas en la auditoría
# ─────────────────────────────────────────────────────────────────────


def test_violencia_severa_preservada(df):
    """Los 33 casos de violencia severa de QS711 sobreviven a la limpieza.

    Es la comprobación de la trampa §7.1: el diccionario del INEI etiqueta
    los códigos 8 y 9, pero los datos graban 3 y 4. Recodificar por convención
    los habría destruido.
    """
    severos = df.violencia_max.isin([3, 4]).sum()
    assert severos >= 33, f"Se perdieron casos severos: quedan {severos}"


def test_no_hay_variables_con_fuga(df):
    """Las variables con fuga de información no entran al dataset analítico."""
    presentes = [v for v in cfg.VARIABLES_CON_FUGA if v in df.columns]
    assert not presentes, f"Variables con fuga en el dataset: {presentes}"


def test_imc_plausible(df):
    """El IMC vive en un rango humano: la escala de peso y talla es correcta."""
    imc = df.imc.dropna()
    assert imc.min() >= 12
    assert imc.max() <= 70
    assert 25 < imc.mean() < 30


def test_antropometria_sin_codigos_de_no_medicion(df):
    """No queda ningún 999.9 en peso, talla ni perímetro abdominal."""
    for c in ("peso_kg", "talla_cm", "perimetro_abdominal"):
        assert (df[c].dropna() < cfg.UMBRAL_NO_MEDICION).all()


def test_presion_arterial_no_fue_filtrada(df):
    """La presión arterial conserva su N: no usa el código 999.9."""
    assert df.presion_sistolica.notna().sum() >= 30_000


# ─────────────────────────────────────────────────────────────────────
# Variables derivadas
# ─────────────────────────────────────────────────────────────────────


def test_region_natural_completa(df):
    """Las tres regiones naturales están representadas, sin categorías huérfanas."""
    vc = df.region_natural.value_counts()
    assert set(vc.index) == set(cfg.REGIONES_NATURALES)
    assert (vc > 1_000).all()


def test_departamentos_completos(df):
    """Los 25 departamentos están presentes."""
    assert df.departamento.nunique() == 25


def test_departamento_normalizado_sin_espacios(df):
    """El nombre normalizado no trae espacios ni minúsculas: cruza con el GeoJSON."""
    s = df.departamento_norm.dropna().unique()
    assert all(x == x.strip() and x == x.upper() for x in s)


def test_edad_en_rango(df):
    """La edad va de 15 a 97, con 97 como tope superior."""
    e = df.edad.dropna()
    assert e.min() >= 15
    assert e.max() <= cfg.EDAD_TOPE


def test_violencia_solo_en_subpoblacion(df):
    """violencia_fisica solo está definida para quienes tuvieron pareja.

    Quien no tuvo pareja no es un "0 de violencia": es otra subpoblación.
    """
    sin_pareja = df.estado_pareja == "Sin pareja"
    assert df.loc[sin_pareja, "violencia_fisica"].isna().all()
    con_pareja = df.estado_pareja == "Con pareja"
    assert int(con_pareja.sum()) == 19_841


def test_no_aplica_codificado_como_cero(df):
    """Quien nunca bebió tiene 0 criterios de abuso, no NaN."""
    nunca = df.consumo_alcohol_12m == 0
    assert (df.loc[nunca, "n_criterios_abuso"] == 0).all()

    no_fumo = df.fuma_12m == 0
    assert (df.loc[no_fumo, "fuma_diario"] == 0).all()


def test_brecha_atencion_solo_en_casos(df):
    """La brecha de atención solo se calcula entre quienes tienen depresión."""
    assert df.loc[df.depresion_bin != 1, "brecha_atencion"].isna().all()
    brecha = df.loc[df.depresion_bin == 1, "brecha_atencion"].mean()
    assert brecha == pytest.approx(0.875, abs=0.01)


def test_faltantes_de_covariables_bajo_umbral(df):
    """Ninguna covariable clave supera el 5 % de faltantes en la población de análisis.

    Si lo superase, el §10.7 exige un análisis de sensibilidad con imputación
    múltiple.
    """
    base = df[df.en_analisis == 1]
    for c in ("edad", "es_mujer", "educacion_grupo", "area", "region_natural"):
        pct = base[c].isna().mean()
        assert pct < 0.05, f"{c} tiene {pct:.1%} de faltantes"


# ─────────────────────────────────────────────────────────────────────
# Correspondencia de los ítems del PHQ-9
# ─────────────────────────────────────────────────────────────────────


def test_el_item_sensible_es_el_menos_endosado(df):
    """El ítem de autolesión debe ser el de menor frecuencia de los nueve.

    La ENDES no numera el PHQ-9 en el orden canónico: su ítem I es «se sintió
    mal consigo mismo», que en el instrumento original es el 6, y el de
    pensamientos de hacerse daño es el H. Escribir el orden estándar de memoria
    marca como sensible el ítem equivocado, y entonces el detector de crisis
    del agente vigila la pregunta que no es.

    Que el ítem declarado sensible sea el menos endosado de los nueve es la
    comprobación empírica de que la correspondencia sigue siendo la correcta.
    """
    frecuencias = {v: (df[v] > 0).mean() for v in cfg.ITEMS_PHQ9}
    menos_endosado = min(frecuencias, key=frecuencias.get)
    assert menos_endosado == cfg.ITEM_SENSIBLE, (
        f"{cfg.ITEM_SENSIBLE} está declarado como ítem sensible, pero el menos "
        f"endosado es {menos_endosado}. Revisa cfg.ETIQUETAS_PHQ9.")


def test_la_etiqueta_del_item_sensible_habla_de_hacerse_dano(df):
    """La etiqueta y la constante deben referirse a lo mismo."""
    etiqueta = cfg.ETIQUETAS_PHQ9[cfg.ITEM_SENSIBLE].lower()
    assert "daño" in etiqueta or "dano" in etiqueta


def test_los_nueve_items_estan_etiquetados(df):
    """Un ítem sin etiqueta rompería el diccionario en silencio."""
    assert set(cfg.ITEMS_PHQ9) == set(cfg.ETIQUETAS_PHQ9)
