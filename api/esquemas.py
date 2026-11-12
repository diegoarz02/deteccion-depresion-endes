"""Esquemas Pydantic v2 de entrada y salida de la API.

La validación es estricta a propósito: es preferible un error claro a una
predicción sobre un perfil imposible.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

DISCLAIMER = (
    "Esta herramienta estima riesgo epidemiológico con fines académicos y de salud "
    "pública. No constituye un diagnóstico médico ni reemplaza la evaluación de un "
    "profesional de salud mental."
)

LINEA_AYUDA = (
    "Si te sientes mal, busca ayuda profesional. En el Perú puedes llamar "
    "gratuitamente a la Línea 113, opción 5 (salud mental), del MINSA."
)


class Sexo(StrEnum):
    """Sexo de la persona."""

    HOMBRE = "Hombre"
    MUJER = "Mujer"


class GrupoEtario(StrEnum):
    """Grupo etario según la categorización del estudio."""

    G15_19 = "15-19"
    G20_29 = "20-29"
    G30_39 = "30-39"
    G40_49 = "40-49"
    G50_59 = "50-59"
    G60 = "60+"


class NivelEducativo(StrEnum):
    """Nivel educativo agrupado."""

    PRIMARIA = "Primaria o menos"
    SECUNDARIA = "Secundaria"
    SUPERIOR = "Superior"


class RegionNatural(StrEnum):
    """Región natural derivada por altitud del conglomerado."""

    COSTA = "Costa"
    SIERRA = "Sierra"
    SELVA = "Selva"


class Area(StrEnum):
    """Área de residencia."""

    URBANO = "Urbano"
    RURAL = "Rural"


class CategoriaRiesgo(StrEnum):
    """Categoría de riesgo relativa a la prevalencia nacional."""

    BAJO = "bajo"
    MEDIO = "medio"
    ALTO = "alto"


class Perfil(BaseModel):
    """Perfil de una persona para estimar su riesgo epidemiológico."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "sexo": "Mujer", "grupo_etario": "60+",
                "nivel_educativo": "Primaria o menos", "region_natural": "Sierra",
                "area": "Rural", "edad": 67, "consumo_frecuente_alcohol": False,
                "consumo_problematico_alcohol": False, "fuma_12m": False,
                "hipertension": True, "diabetes": False, "obesidad": True,
            }
        },
    )

    sexo: Sexo
    grupo_etario: GrupoEtario
    nivel_educativo: NivelEducativo
    region_natural: RegionNatural
    area: Area
    edad: Annotated[int, Field(ge=15, le=97, description="Años cumplidos, entre 15 y 97")] = 35

    consumo_frecuente_alcohol: bool = Field(
        False, description="Consumió alcohol 12 o más días en los últimos 12 meses")
    consumo_problematico_alcohol: bool = Field(
        False, description="Dos o más criterios de abuso de alcohol")
    fuma_12m: bool = Field(False, description="Fumó cigarrillos en los últimos 12 meses")
    hipertension: bool = Field(False, description="Hipertensión arterial diagnosticada")
    diabetes: bool = Field(False, description="Diabetes diagnosticada")
    obesidad: bool = Field(False, description="Índice de masa corporal igual o mayor a 30")

    # ── Señales de seguridad ─────────────────────────────────────────
    #
    # Estos dos campos NO son predictores y nunca entran al modelo: serían fuga
    # de información, porque el puntaje PHQ-9 *es* el desenlace. Existen para
    # una única cosa: permitir que el nodo de crisis actúe antes de que se
    # redacte nada. Si la aplicación recoge las respuestas del cuestionario,
    # tiene la obligación de mirarlas.
    altitud: Annotated[int | None, Field(
        ge=0, le=5000,
        description="Altitud de residencia en metros, si se conoce")] = None
    item_autolesion: Annotated[int | None, Field(
        ge=0, le=3,
        description="Respuesta al ítem de pensamientos de hacerse daño (0-3). "
                    "En la ENDES es QS700H, no QS700I: el cuestionario no sigue "
                    "el orden canónico del PHQ-9. Solo se usa para activar la "
                    "detección de crisis; no es un predictor del modelo.")] = None
    phq9_score: Annotated[int | None, Field(
        ge=0, le=27,
        description="Puntaje PHQ-9 total, si la persona respondió el cuestionario. "
                    "Solo se usa para la detección de crisis; no es un predictor.")] = None
    violencia_pareja: bool = Field(
        False, description="Sufrió violencia física de pareja en los últimos 12 meses. "
                           "Se usa para ofrecer los recursos adecuados.")

    @field_validator("edad")
    @classmethod
    def edad_coherente_con_grupo(cls, v: int, info) -> int:
        """Comprueba que la edad declarada caiga dentro de su grupo etario."""
        grupo = info.data.get("grupo_etario")
        if grupo is None:
            return v
        rangos = {"15-19": (15, 19), "20-29": (20, 29), "30-39": (30, 39),
                  "40-49": (40, 49), "50-59": (50, 59), "60+": (60, 97)}
        lo, hi = rangos[grupo.value]
        if not lo <= v <= hi:
            raise ValueError(
                f"La edad {v} no corresponde al grupo etario {grupo.value} ({lo}-{hi})")
        return v


class FactorContribuyente(BaseModel):
    """Característica que más se asocia con la estimación de un perfil.

    Describe asociación ajustada (odds ratio), no un efecto causal: el estudio es
    transversal y mide exposición y resultado a la vez.
    """

    factor: str
    contribucion_log_odds: float
    odds_ratio: float


class Prediccion(BaseModel):
    """Resultado de la estimación de riesgo para un perfil."""

    probabilidad: float = Field(..., ge=0, le=1)
    probabilidad_pct: float
    categoria_riesgo: CategoriaRiesgo
    prevalencia_nacional: float
    #: Razón de prevalencias: cociente entre la estimación del perfil y la
    #: prevalencia nacional. No es un riesgo relativo.
    razon_sobre_prevalencia: float
    factores_contribuyentes: list[FactorContribuyente]
    disclaimer: str = DISCLAIMER
    linea_ayuda: str = LINEA_AYUDA


class Salud(BaseModel):
    """Estado del servicio."""

    estado: str
    modelo_cargado: bool
    version: str


class InfoModelo(BaseModel):
    """Metadatos del modelo desplegado."""

    tipo: str
    desenlace: str
    instrumento: str
    punto_de_corte: int
    n_entrenamiento: int
    prevalencia: float
    auc: float
    brier: float
    variables: list[str]
    fuente: str
    disclaimer: str = DISCLAIMER
    usos_prohibidos: list[str]


class LoteEntrada(BaseModel):
    """Lote de perfiles para predicción masiva."""

    model_config = ConfigDict(extra="forbid")

    perfiles: Annotated[list[Perfil], Field(min_length=1, max_length=500)]


class LoteSalida(BaseModel):
    """Resultado de una predicción por lotes."""

    n: int
    predicciones: list[Prediccion]
    disclaimer: str = DISCLAIMER


class Interpretacion(BaseModel):
    """Interpretación en lenguaje natural generada por el agente."""

    texto: str
    modo: str = Field(..., description="'llm' o 'degradado'")
    prediccion: Prediccion
    trazas: list[dict]
