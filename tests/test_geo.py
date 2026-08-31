"""Tests del módulo de georreferenciación (Fase 2).

La corrección de coordenadas es una transformación silenciosa: si se equivoca,
no lanza ningún error, simplemente coloca personas en el país equivocado y todos
los mapas posteriores quedan mal sin que nada avise. Estos tests son el único
sitio donde esa clase de fallo se hace visible.

Ejecutar con::

    pytest tests/test_geo.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "codigo" / "src"))

from depresion import config as cfg  # noqa: E402
from depresion import geo  # noqa: E402

# ─────────────────────────────────────────────────────────────────────
# Corrección de coordenadas
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def coordenadas() -> pd.DataFrame:
    """Cuatro casos que cubren las cuatro ramas de la corrección.

    Lima (-77,0 / -12,0) llega bien; el segundo es el mismo punto con los campos
    intercambiados; el tercero está en Madrid, que no se arregla intercambiando;
    el cuarto no tiene dato.
    """
    return pd.DataFrame({
        "LONGITUDX": [-77.03, -12.05, -3.70, np.nan],
        "LATITUDY": [-12.05, -77.03, 40.42, np.nan],
    })


def test_coordenada_correcta_no_se_toca(coordenadas):
    """Un punto ya válido debe salir idéntico."""
    out, _ = geo.corregir_coordenadas(coordenadas)
    assert out.longitud.iloc[0] == pytest.approx(-77.03)
    assert out.latitud.iloc[0] == pytest.approx(-12.05)
    assert out.coord_estado.iloc[0] == "correcta"


def test_coordenada_invertida_se_intercambia(coordenadas):
    """El caso invertido debe acabar en el mismo lugar que el correcto."""
    out, _ = geo.corregir_coordenadas(coordenadas)
    assert out.longitud.iloc[1] == pytest.approx(-77.03)
    assert out.latitud.iloc[1] == pytest.approx(-12.05)
    assert out.coord_estado.iloc[1].startswith("corregida")


def test_coordenada_fuera_del_pais_se_descarta(coordenadas):
    """Madrid no se arregla intercambiando: debe quedar como faltante.

    Es la decisión importante del módulo: perder el punto antes que situarlo mal.
    """
    out, _ = geo.corregir_coordenadas(coordenadas)
    assert pd.isna(out.longitud.iloc[2])
    assert pd.isna(out.latitud.iloc[2])
    assert out.coord_estado.iloc[2].startswith("descartada")


def test_las_tres_categorias_son_excluyentes(coordenadas):
    """Ninguna fila puede contarse en dos grupos de la bitácora."""
    _, bitacora = geo.corregir_coordenadas(coordenadas)
    assert bitacora.n.sum() == len(coordenadas)


def test_correccion_es_idempotente(coordenadas):
    """Aplicarla dos veces no debe volver a intercambiar nada.

    Si no lo fuera, reejecutar el pipeline movería los puntos.
    """
    out1, _ = geo.corregir_coordenadas(coordenadas)
    reentrada = out1[["longitud", "latitud"]].rename(
        columns={"longitud": "LONGITUDX", "latitud": "LATITUDY"})
    out2, bit2 = geo.corregir_coordenadas(reentrada)
    assert bit2.loc[bit2.grupo == "Intercambiadas", "n"].iloc[0] == 0
    pd.testing.assert_series_equal(out1.longitud, out2.longitud, check_names=False)


def test_ningun_punto_valido_cae_fuera_del_peru(coordenadas):
    """Tras corregir, todo lo que sobrevive está dentro del recuadro del país."""
    out, _ = geo.corregir_coordenadas(coordenadas)
    v = out.dropna(subset=["longitud", "latitud"])
    assert v.longitud.between(*geo.LONGITUD_PERU).all()
    assert v.latitud.between(*geo.LATITUD_PERU).all()


# ─────────────────────────────────────────────────────────────────────
# Pisos altitudinales
# ─────────────────────────────────────────────────────────────────────


def test_pisos_altitudinales_cubren_sin_solapar():
    """Los tramos deben encajar exactamente: sin huecos ni solapes."""
    for (_, hi_a, _), (lo_b, _, _) in zip(geo.PISOS_ALTITUDINALES,
                                          geo.PISOS_ALTITUDINALES[1:], strict=False):
        assert hi_a == lo_b


def test_altitud_se_clasifica_en_el_piso_correcto():
    """Un valor en cada tramo y en cada frontera cae donde debe."""
    d = pd.DataFrame({cfg.VAR_ALTITUD: [0, 499, 500, 1999, 2000, 2999, 3000, 3999, 4000, 4800]})
    out = geo.construir_altitud(d)
    esperado = ["Costa / selva baja (0-499 m)", "Costa / selva baja (0-499 m)",
                "Yunga (500-1 999 m)", "Yunga (500-1 999 m)",
                "Quechua (2 000-2 999 m)", "Quechua (2 000-2 999 m)",
                "Suni (3 000-3 999 m)", "Suni (3 000-3 999 m)",
                "Puna (4 000 m o más)", "Puna (4 000 m o más)"]
    assert list(out.altitud_categoria.astype(str)) == esperado


def test_piso_altitudinal_es_ordinal():
    """El orden importa: los gráficos y los contrastes de tendencia lo usan."""
    d = pd.DataFrame({cfg.VAR_ALTITUD: [100, 3500]})
    out = geo.construir_altitud(d)
    assert out.altitud_categoria.cat.ordered
    assert list(out.altitud_categoria.cat.categories) == geo.ORDEN_PISOS


def test_gran_altitud_respeta_el_corte_de_2500():
    """El umbral de 2 500 m es el de la literatura; no debe deslizarse."""
    d = pd.DataFrame({cfg.VAR_ALTITUD: [2499, 2500, np.nan]})
    out = geo.construir_altitud(d)
    assert out.gran_altitud.iloc[0] == 0
    assert out.gran_altitud.iloc[1] == 1
    assert pd.isna(out.gran_altitud.iloc[2])


def test_altitud_faltante_no_inventa_categoria():
    """Sin altitud no hay piso: no debe caer en el primero por defecto."""
    d = pd.DataFrame({cfg.VAR_ALTITUD: [np.nan, -1]})
    out = geo.construir_altitud(d)
    assert out.altitud_categoria.isna().all()


# ─────────────────────────────────────────────────────────────────────
# Agregación territorial
# ─────────────────────────────────────────────────────────────────────


def test_territorio_pequeno_no_publica_prevalencia():
    """Un territorio por debajo del mínimo no debe aportar una cifra al mapa.

    Es la salvaguarda que evita que un distrito con 8 personas pinte del color
    más intenso del mapa por azar muestral.
    """
    d = pd.DataFrame({
        "cod": ["A"] * 60 + ["B"] * 10,
        "depresion_bin": [1] * 6 + [0] * 54 + [1] * 5 + [0] * 5,
        "peso": 1.0,
    })
    out = geo.agregar_por_territorio(d, "cod").set_index("cod")
    assert out.loc["A", "estimable"]
    assert not out.loc["B", "estimable"]
    assert pd.isna(out.loc["B", "prevalencia"])
    assert out.loc["A", "prevalencia"] == pytest.approx(10.0)


def test_agregacion_usa_el_ponderador():
    """La prevalencia territorial es ponderada, no cruda."""
    d = pd.DataFrame({
        "cod": ["A"] * 100,
        "depresion_bin": [1] * 50 + [0] * 50,
        "peso": [3.0] * 50 + [1.0] * 50,
    })
    out = geo.agregar_por_territorio(d, "cod")
    assert out.prevalencia.iloc[0] == pytest.approx(75.0)


def test_agregacion_no_muta_la_entrada():
    """Un helper que modifica el DataFrame de quien lo llama es una trampa."""
    d = pd.DataFrame({"cod": ["A"] * 60, "depresion_bin": [0] * 60, "peso": 1.0})
    antes = d.copy()
    geo.agregar_por_territorio(d, "cod")
    pd.testing.assert_frame_equal(d, antes)
