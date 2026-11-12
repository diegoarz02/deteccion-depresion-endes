"""Pruebas de las medidas de asociación y de impacto basadas en prevalencia.

Las funciones puras se comprueban contra valores que se pueden verificar a mano.
Las tablas generadas se cotejan entre sí: la 2×2 con la tabla 12 de OR y RP, y
las fracciones atribuibles con sus identidades algebraicas.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "codigo" / "src"))
sys.path.insert(0, str(RAIZ / "codigo" / "scripts"))

from depresion import atribuible as atr  # noqa: E402
from depresion import config as cfg  # noqa: E402

# Tabla de ejemplo con resultados que se verifican a mano:
#              con desenlace   sin desenlace
# expuestos         20              80       n1 = 100
# no expuestos      10              90       n0 = 100
A, B, C, D = 20, 80, 10, 90


class TestTabla2x2:
    """La notación a, b, c, d y las medidas que salen de ella."""

    def test_celdas_abcd_cuenta_bien(self):
        e = pd.Series([1] * 100 + [0] * 100)
        y = pd.Series([1] * 20 + [0] * 80 + [1] * 10 + [0] * 90)
        assert atr.celdas_abcd(e, y) == {"a": A, "b": B, "c": C, "d": D}

    def test_celdas_descarta_faltantes_por_pares(self):
        e = pd.Series([1, 1, 0, 0, np.nan])
        y = pd.Series([1, 0, 1, 0, 1])
        assert sum(atr.celdas_abcd(e, y).values()) == 4

    def test_or_rp_rd(self):
        m = atr.medidas_2x2(A, B, C, D)
        assert m["or"] == pytest.approx(2.25)
        assert m["rp"] == pytest.approx(2.0)
        assert m["rd"] == pytest.approx(10.0)

    def test_chi_cuadrado_a_mano(self):
        # n (ad - bc)^2 / (n1 n0 m1 m0) = 200 * 1e6 / (100 * 100 * 30 * 170)
        m = atr.medidas_2x2(A, B, C, D)
        assert m["chi2"] == pytest.approx(200 * 1e6 / (100 * 100 * 30 * 170))
        assert 0 < m["p_chi2"] < 1

    def test_intervalos_contienen_la_estimacion(self):
        m = atr.medidas_2x2(A, B, C, D)
        assert m["or_ic_inf"] < m["or"] < m["or_ic_sup"]
        assert m["rp_ic_inf"] < m["rp"] < m["rp_ic_sup"]

    def test_lectura_de_la_fuerza(self):
        assert "factor de riesgo, con asociación marcada" in atr.fuerza(3.5, 2.9, 4.2)
        assert "factor protector, con asociación discreta" in atr.fuerza(0.75, 0.64, 0.88)
        assert "nulidad" in atr.fuerza(1.09, 0.99, 1.21)


class TestFraccionesAtribuibles:
    """Las identidades que deben cumplirse."""

    def test_fraccion_en_expuestos(self):
        assert atr.fraccion_en_expuestos(2.0) == pytest.approx(0.5)
        assert atr.fraccion_en_expuestos(1.0) == pytest.approx(0.0)

    def test_levin_y_miettinen_coinciden_con_medidas_crudas(self):
        """Sin ajuste, las dos fórmulas de la fracción poblacional son la misma."""
        m = atr.medidas_2x2(A, B, C, D)
        rp = m["rp"]
        pe = (A + B) / (A + B + C + D)
        pc = A / (A + C)
        assert atr.paf_levin(pe, rp) == pytest.approx(atr.paf_miettinen(pc, rp))

    def test_paf_es_nula_sin_asociacion(self):
        assert atr.paf_levin(0.3, 1.0) == pytest.approx(0.0)
        assert atr.paf_miettinen(0.3, 1.0) == pytest.approx(0.0)

    def test_paf_crece_con_la_frecuencia_de_la_exposicion(self):
        """Una asociación fuerte sobre una exposición rara pesa menos que una moderada y común."""
        rara_y_fuerte = atr.paf_levin(0.01, 5.0)
        comun_y_moderada = atr.paf_levin(0.30, 1.4)
        assert rara_y_fuerte < comun_y_moderada


class TestReplicasRaoWu:
    """El remuestreo de conglomerados dentro de estratos."""

    @pytest.fixture()
    def diseno(self):
        rng = np.random.default_rng(1)
        # 6 estratos de 8 conglomerados y 5 personas cada uno, más un estrato con un solo conglomerado
        estrato = np.repeat(np.arange(6), 8 * 5)
        conglomerado = np.repeat(np.arange(48), 5)
        estrato = np.concatenate([estrato, np.full(5, 99)])
        conglomerado = np.concatenate([conglomerado, np.full(5, 999)])
        return estrato, conglomerado, rng

    def test_los_pesos_se_conservan_en_promedio(self, diseno):
        estrato, conglomerado, _ = diseno
        rep = atr.ReplicasRaoWu(estrato, conglomerado, semilla=7)
        medias = [rep.factores().mean() for _ in range(300)]
        assert np.mean(medias) == pytest.approx(1.0, abs=0.02)

    def test_el_estrato_con_un_conglomerado_no_cambia(self, diseno):
        estrato, conglomerado, _ = diseno
        rep = atr.ReplicasRaoWu(estrato, conglomerado, semilla=7)
        for _ in range(20):
            f = rep.factores()
            assert np.all(f[estrato == 99] == 1.0)

    def test_misma_semilla_misma_replica(self, diseno):
        estrato, conglomerado, _ = diseno
        a = atr.ReplicasRaoWu(estrato, conglomerado, semilla=3).factores()
        b = atr.ReplicasRaoWu(estrato, conglomerado, semilla=3).factores()
        assert np.array_equal(a, b)


class TestTablasGeneradas:
    """Coherencia entre las tablas que escribe el análisis."""

    @pytest.fixture(scope="class")
    def t57(self) -> pd.DataFrame:
        ruta = cfg.TABLAS / "tabla_57_asociacion_2x2.csv"
        if not ruta.exists():
            pytest.skip("falta tabla_57: ejecuta analisis_12_asociacion_atribuible.py")
        return pd.read_csv(ruta, encoding="utf-8-sig")

    def test_la_2x2_cuadra_con_la_tabla_12(self, t57):
        ruta = cfg.TABLAS / "tabla_12_or_y_rp.csv"
        if not ruta.exists():
            pytest.skip("falta tabla_12")
        t12 = pd.read_csv(ruta, encoding="utf-8-sig").set_index("variable")
        t = t57.set_index("variable")
        assert (t["or"] - t12["or"]).abs().max() < 5e-3
        assert (t["rp"] - t12["rp"]).abs().max() < 5e-3

    def test_las_celdas_suman_el_total(self, t57):
        assert (t57.a + t57.b + t57.c + t57.d == t57.n).all()

    def test_la_lectura_respeta_el_diseno(self, t57):
        """Si Rao y Scott no rechaza, la lectura no puede declarar una asociación."""
        sin_senal = t57[t57.p_rao_scott >= 0.05]
        assert sin_senal.lectura.str.contains("nulidad").all()

    def test_las_fracciones_cumplen_su_identidad(self):
        ruta = cfg.TABLAS / "tabla_58_riesgo_atribuible.csv"
        if not ruta.exists():
            pytest.skip("falta tabla_58")
        t = pd.read_csv(ruta, encoding="utf-8-sig")
        esperado = (t.rp_ajustada - 1) / t.rp_ajustada * 100
        assert np.allclose(t.afe_ajustada, esperado, atol=0.05)

    def test_las_replicas_coinciden_con_taylor(self):
        """Control cruzado de los dos métodos de varianza para la razón de prevalencias."""
        ruta = cfg.TABLAS / "tabla_58_riesgo_atribuible.csv"
        if not ruta.exists():
            pytest.skip("falta tabla_58")
        t = pd.read_csv(ruta, encoding="utf-8-sig")
        ancho_taylor = np.log(t.rp_ajustada_ic_sup / t.rp_ajustada_ic_inf)
        ancho_boot = np.log(t.rp_ajustada_boot_sup / t.rp_ajustada_boot_inf)
        assert (ancho_boot / ancho_taylor).between(0.8, 1.25).all()


class TestAltitudComoConfusor:
    """Las tablas de altitud responden lo que dicen responder."""

    def test_ningun_factor_supera_el_umbral(self):
        ruta = cfg.TABLAS / "tabla_59_altitud_confusor_de_otros_factores.csv"
        if not ruta.exists():
            pytest.skip("falta tabla_59: ejecuta analisis_13_altitud_confusor.py")
        t = pd.read_csv(ruta, encoding="utf-8-sig")
        assert (t.confunde == (t.cambio_pct.abs() >= 10)).all()

    def test_la_cadena_reproduce_la_tabla_38(self):
        """El escalonado debe volver a dar los modelos (b) y (c) de la tabla 38."""
        r13 = cfg.TABLAS / "tabla_60_altitud_cruda_vs_ajustada.csv"
        r38 = cfg.TABLAS / "tabla_38_altitud_modelos.csv"
        if not (r13.exists() and r38.exists()):
            pytest.skip("faltan tablas 38 o 60")
        t60 = pd.read_csv(r13, encoding="utf-8-sig").set_index("modelo")
        t38 = pd.read_csv(r38, encoding="utf-8-sig").set_index("modelo")
        c4 = next(i for i in t60.index if i.startswith("(4)") and "*" not in i)
        c5 = next(i for i in t60.index if i.startswith("(5)"))
        assert t60.loc[c4, "or_por_1000m"] == pytest.approx(t38.loc["(b) Ajustada", "por_1000m"], abs=2e-3)
        assert t60.loc[c5, "or_por_1000m"] == pytest.approx(
            t38.loc["(c) Ajustada + región", "por_1000m"], abs=2e-3)


class TestSinEducacion:
    """El nivel educativo ausente es un salto del cuestionario, no una omisión."""

    def test_las_nulas_son_quienes_nunca_asistieron(self):
        from depresion import sensibilidad as sens

        df = pd.read_parquet(cfg.DATASET_FINAL)
        base = df[df.en_analisis == 1]
        r = sens.verificar_sin_educacion(base)
        if not r.get("verificado"):
            pytest.skip("no están los .sav originales para verificar contra QS24")
        assert r["salto_estructural"]
        assert r["nulas_en_analisis"] == r["nulas_que_nunca_asistieron"]

    def test_la_categoria_nueva_cubre_todas_las_nulas(self):
        from depresion import sensibilidad as sens

        df = pd.read_parquet(cfg.DATASET_FINAL)
        base = sens.educacion_cuatro_niveles(df[df.en_analisis == 1])
        assert base.educacion_4.notna().all()
        assert (base.educacion_4 == sens.SIN_EDUCACION).sum() == base.educacion_grupo.isna().sum()
