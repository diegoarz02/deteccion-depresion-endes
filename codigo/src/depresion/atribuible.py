"""Medidas de asociación y de impacto basadas en prevalencia.

En un estudio transversal no hay incidencia, así que no existe el riesgo
relativo clásico. Lo que sí se estima es la **razón de prevalencias** (RP) y,
sobre ella, las versiones del riesgo atribuible que se apoyan en prevalencia:

* diferencia de prevalencias entre expuestos y no expuestos (RD),
* fracción atribuible en los expuestos (``(RP - 1) / RP``),
* fracción atribuible poblacional (PAF), por la fórmula de Levin cuando las
  medidas son crudas y por la de Miettinen cuando la RP viene ajustada.

Ninguna de estas fracciones es una fracción *prevenible* salvo que la
asociación sea causal y no esté confundida. El diseño no permite verificarlo,
y la salida lo dice así.

Las réplicas bootstrap siguen a Rao y Wu (1988): ``n_h - 1`` conglomerados por
estrato, con los pesos reescalados, de modo que la varianza del diseño
estratificado por conglomerados se reproduce sin sesgo.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

Z95 = 1.959963984540054


# ─────────────────────────────────────────────────────────────────────
# Tabla 2x2 en notación a, b, c, d
# ─────────────────────────────────────────────────────────────────────


def celdas_abcd(expuesto: pd.Series, desenlace: pd.Series) -> dict[str, int]:
    """Cuenta las cuatro celdas de la tabla 2×2.

    ``a``: expuestos con el desenlace; ``b``: expuestos sin él;
    ``c``: no expuestos con el desenlace; ``d``: no expuestos sin él.
    Los faltantes se descartan por pares.
    """
    d = pd.DataFrame({"e": expuesto, "y": desenlace}).dropna()
    e = d.e.astype(int).to_numpy()
    y = d.y.astype(int).to_numpy()
    return {
        "a": int(((e == 1) & (y == 1)).sum()),
        "b": int(((e == 1) & (y == 0)).sum()),
        "c": int(((e == 0) & (y == 1)).sum()),
        "d": int(((e == 0) & (y == 0)).sum()),
    }


def medidas_2x2(a: int, b: int, c: int, d: int) -> dict[str, float]:
    """Calcula las medidas clásicas de una tabla 2×2 con IC 95 %.

    El OR usa el error estándar de Woolf; la RP, el del logaritmo de un
    cociente de proporciones (Katz); la diferencia de prevalencias, el de Wald.
    La prueba chi cuadrado es la de Pearson **sin** corrección de continuidad,
    con 1 grado de libertad, y supone observaciones independientes: con un
    muestreo por conglomerados es optimista, y por eso se acompaña de la
    versión de Rao y Scott en el script que la llama.
    """
    n1, n0 = a + b, c + d
    m1, m0 = a + c, b + d
    n = n1 + n0
    p1, p0 = a / n1, c / n0

    or_ = (a * d) / (b * c)
    se_or = np.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    rp = p1 / p0
    se_rp = np.sqrt(1 / a - 1 / n1 + 1 / c - 1 / n0)
    rd = p1 - p0
    se_rd = np.sqrt(p1 * (1 - p1) / n1 + p0 * (1 - p0) / n0)

    chi2 = n * (a * d - b * c) ** 2 / (n1 * n0 * m1 * m0)
    esperada_minima = min(n1 * m1, n1 * m0, n0 * m1, n0 * m0) / n

    return {
        "n": n, "n_expuestos": n1, "n_no_expuestos": n0,
        "prev_expuestos": p1 * 100, "prev_no_expuestos": p0 * 100,
        "or": or_, "or_ic_inf": np.exp(np.log(or_) - Z95 * se_or),
        "or_ic_sup": np.exp(np.log(or_) + Z95 * se_or),
        "rp": rp, "rp_ic_inf": np.exp(np.log(rp) - Z95 * se_rp),
        "rp_ic_sup": np.exp(np.log(rp) + Z95 * se_rp),
        "rd": rd * 100, "rd_ic_inf": (rd - Z95 * se_rd) * 100,
        "rd_ic_sup": (rd + Z95 * se_rd) * 100,
        "chi2": chi2, "p_chi2": float(stats.chi2.sf(chi2, 1)),
        "esperada_minima": esperada_minima,
    }


def fuerza(medida: float, ic_inf: float, ic_sup: float) -> str:
    """Lee una razón (OR o RP) como factor de riesgo, protector o sin señal.

    La gradación es una convención práctica, no una norma: menos de 1,5 discreta,
    de 1,5 a menos de 3 moderada, 3 o más marcada; para un efecto protector se
    aplica sobre el inverso de la razón.
    """
    if ic_inf <= 1 <= ic_sup:
        return "sin asociación distinguible de la nulidad"
    x = medida if medida > 1 else 1 / medida
    grado = "discreta" if x < 1.5 else ("moderada" if x < 3 else "marcada")
    tipo = "factor de riesgo" if medida > 1 else "factor protector"
    return f"{tipo}, con asociación {grado}"


# ─────────────────────────────────────────────────────────────────────
# Fracciones atribuibles basadas en prevalencia
# ─────────────────────────────────────────────────────────────────────


def fraccion_en_expuestos(rp: float) -> float:
    """Fracción atribuible en los expuestos: ``(RP - 1) / RP``."""
    return (rp - 1) / rp


def paf_levin(p_exposicion: float, rp: float) -> float:
    """Fracción atribuible poblacional de Levin.

    ``Pe (RP - 1) / (1 + Pe (RP - 1))``, con ``Pe`` la prevalencia de la
    exposición en la población. Es exacta con medidas crudas; con una RP
    ajustada sesga, y entonces corresponde la de Miettinen.
    """
    x = p_exposicion * (rp - 1)
    return x / (1 + x)


def paf_miettinen(p_casos_expuestos: float, rp: float) -> float:
    """Fracción atribuible poblacional de Miettinen (1974).

    ``Pc (RP - 1) / RP``, con ``Pc`` la proporción de casos que estaban
    expuestos. Con una RP ajustada por confusores es la forma recomendada
    (Rockhill et al., 1998).
    """
    return p_casos_expuestos * (rp - 1) / rp


# ─────────────────────────────────────────────────────────────────────
# Réplicas bootstrap del diseño (Rao y Wu, 1988)
# ─────────────────────────────────────────────────────────────────────


class ReplicasRaoWu:
    """Genera factores de reescalado de pesos por remuestreo de conglomerados.

    En cada estrato con ``n_h >= 2`` conglomerados se sortean ``n_h - 1`` con
    reemplazo y cada conglomerado recibe el factor ``n_h / (n_h - 1)`` por el
    número de veces que salió. Los estratos con un solo conglomerado conservan
    su peso: no aportan varianza, que es lo mismo que hace el centrado en la
    media general con el que se declaró el diseño.
    """

    def __init__(self, estrato: np.ndarray, conglomerado: np.ndarray, semilla: int = 42):
        clave = pd.MultiIndex.from_arrays([estrato, conglomerado])
        self.id_psu, psus = pd.factorize(clave)
        self.n_psu = len(psus)
        # Estrato de cada conglomerado, y tamaño del estrato
        est_de_psu = pd.Series(np.asarray(estrato)).groupby(self.id_psu).first().to_numpy()
        _, cod_estrato = np.unique(est_de_psu, return_inverse=True)
        self.n_h = np.bincount(cod_estrato)[cod_estrato]          # n_h de cada PSU
        orden = np.argsort(cod_estrato, kind="stable")
        self._orden = orden
        self._cod = cod_estrato
        n_estratos = cod_estrato.max() + 1
        tam = np.bincount(cod_estrato, minlength=n_estratos)
        self._tam = tam
        self._inicio = np.concatenate([[0], np.cumsum(tam)[:-1]])
        # Sorteos por estrato: n_h - 1 si n_h >= 2, ninguno si n_h == 1
        self._m = np.where(tam >= 2, tam - 1, 0)
        self._est_sorteo = np.repeat(np.arange(n_estratos), self._m)
        self.rng = np.random.default_rng(semilla)

    def factores(self) -> np.ndarray:
        """Factor de reescalado de cada observación para una réplica."""
        tam = self._tam[self._est_sorteo]
        ini = self._inicio[self._est_sorteo]
        sorteo = ini + self.rng.integers(0, tam)               # posición en el orden
        elegidos = self._orden[sorteo]
        veces = np.bincount(elegidos, minlength=self.n_psu).astype(float)
        factor_psu = np.where(self.n_h >= 2, self.n_h / np.maximum(self.n_h - 1, 1) * veces, 1.0)
        return factor_psu[self.id_psu]


def intervalo_percentil(valores: np.ndarray, nivel: float = 0.95) -> tuple[float, float]:
    """Intervalo de percentiles de una distribución bootstrap."""
    a = (1 - nivel) / 2
    lo, hi = np.nanquantile(valores, [a, 1 - a])
    return float(lo), float(hi)
