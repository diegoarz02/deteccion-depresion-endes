"""Lógica de predicción, independiente del framework web.

Separar esto de ``main.py`` permite probarlo sin levantar el servidor y
reutilizarlo desde el agente de LangGraph.

Se despliega **solo el modelo logístico**, por decisión de arquitectura: es el
modelo del informe, pesa unos kilobytes y arranca al instante. XGBoost y SHAP
se quedan en el análisis local, y los valores SHAP que muestra el boletín están
precalculados. Ver el README para el detalle de esa decisión.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

from esquemas import CategoriaRiesgo, FactorContribuyente, Perfil, Prediccion

log = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parents[1]
RUTA_COEFICIENTES = RAIZ / "resultados" / "modelos" / "coeficientes_logistico.json"
RUTA_DATOS = Path(__file__).resolve().parent / "datos"

# En producción los coeficientes viajan dentro de api/datos/, para que la imagen
# desplegada no necesite la carpeta de resultados del análisis.
RUTA_COEFICIENTES_PROD = RUTA_DATOS / "coeficientes.json"

# Traducción de los campos de la API a los términos del modelo.
MAPA_BOOLEANOS = {
    "consumo_frecuente_alcohol": "consumo_frecuente",
    "consumo_problematico_alcohol": "alcohol_problematico",
    "fuma_12m": "fuma_12m",
    "hipertension": "hta_dx",
    "diabetes": "diabetes_dx",
    "obesidad": "obesidad",
}

ETIQUETAS = {
    "es_mujer": "Sexo femenino",
    "es_rural": "Residencia rural",
    "consumo_frecuente": "Consumo frecuente de alcohol",
    "alcohol_problematico": "Consumo problemático de alcohol",
    "fuma_12m": "Tabaquismo en los últimos 12 meses",
    "hta_dx": "Hipertensión diagnosticada",
    "diabetes_dx": "Diabetes diagnosticada",
    "obesidad": "Obesidad",
}

USOS_PROHIBIDOS = [
    "Diagnosticar depresión en una persona concreta.",
    "Decidir acceso a tratamiento, seguros, empleo o cualquier prestación.",
    "Tamizar sin ofrecer derivación a atención profesional.",
    "Presentar la probabilidad como certeza o sin su incertidumbre.",
    "Analizar o publicar el ítem de autolesión como resultado independiente.",
]


class ModeloNoDisponible(RuntimeError):
    """Se lanza cuando no se pudieron cargar los coeficientes del modelo."""


class Servicio:
    """Encapsula el modelo logístico y la lógica de predicción."""

    def __init__(self) -> None:
        self.coeficientes: dict[str, float] = {}
        self.intercepto: float = 0.0
        self.metadatos: dict = {}
        self.cargado = False

    def cargar(self, ruta: Path | None = None) -> None:
        """Carga los coeficientes desde disco. Se llama una vez, en el lifespan."""
        ruta = ruta or (RUTA_COEFICIENTES if RUTA_COEFICIENTES.exists()
                        else RUTA_COEFICIENTES_PROD)
        if not ruta.exists():
            raise ModeloNoDisponible(f"No se encontró el modelo en {ruta}")
        d = json.loads(ruta.read_text(encoding="utf-8"))
        self.intercepto = float(d["intercepto"])
        self.coeficientes = {k: float(v) for k, v in d["coeficientes"].items()}
        self.metadatos = d
        self.cargado = True
        self._contexto = None
        self._alinear_prevalencia()
        log.info("Modelo cargado: %s coeficientes, AUC %.3f",
                 len(self.coeficientes), d.get("auc", float("nan")))

    def _alinear_prevalencia(self) -> None:
        """Fija como prevalencia nacional de referencia la ponderada (6,98 %).

        Es la estimada con el diseño de la encuesta y la misma que cita el boletín.
        Las probabilidades del modelo salen de una logística con diseño, así que
        están calibradas con ella, y con ella se compara cada perfil. La media sin
        ponderar de la muestra de ajuste queda disponible como
        ``prevalencia_muestra_modelo``.
        """
        nacional = self.contexto().get("nacional", {}).get("prevalencia")
        if nacional:
            self.metadatos["prevalencia_muestra_modelo"] = self.metadatos.get("prevalencia")
            self.metadatos["prevalencia"] = float(nacional) / 100

    def _terminos(self, p: Perfil) -> dict[str, float]:
        """Traduce un perfil a los términos del modelo, con sus valores 0/1."""
        t: dict[str, float] = {"es_mujer": 1.0 if p.sexo.value == "Mujer" else 0.0,
                               "es_rural": 1.0 if p.area.value == "Rural" else 0.0}
        for campo, termino in MAPA_BOOLEANOS.items():
            t[termino] = 1.0 if getattr(p, campo) else 0.0
        # Categóricas: solo la dummy correspondiente, salvo la referencia.
        if p.grupo_etario.value != "30-39":
            t[f"grupo_etario_{p.grupo_etario.value}"] = 1.0
        if p.nivel_educativo.value != "Superior":
            t[f"educacion_grupo_{p.nivel_educativo.value}"] = 1.0
        if p.region_natural.value != "Costa":
            t[f"region_natural_{p.region_natural.value}"] = 1.0
        return t

    def predecir(self, perfil: Perfil) -> Prediccion:
        """Estima la probabilidad de depresión para un perfil.

        Returns
        -------
        Prediccion
            Probabilidad, categoría de riesgo relativa a la prevalencia nacional
            y los tres factores que más contribuyen.

        Raises
        ------
        ModeloNoDisponible
            Si el modelo no se cargó.
        """
        if not self.cargado:
            raise ModeloNoDisponible("El modelo no está cargado")

        terminos = self._terminos(perfil)
        z = self.intercepto
        contribuciones = []
        for termino, valor in terminos.items():
            beta = self.coeficientes.get(termino)
            if beta is None or valor == 0:
                continue
            z += beta * valor
            contribuciones.append((termino, beta))

        prob = 1 / (1 + math.exp(-z))
        prev = float(self.metadatos.get("prevalencia", 0.07))
        razon = prob / prev if prev else float("nan")

        if razon >= 2.5:
            categoria = CategoriaRiesgo.ALTO
        elif razon >= 1.0:
            categoria = CategoriaRiesgo.MEDIO
        else:
            categoria = CategoriaRiesgo.BAJO

        contribuciones.sort(key=lambda x: -x[1])
        factores = [
            FactorContribuyente(
                factor=ETIQUETAS.get(t, self._etiqueta_categorica(t)),
                contribucion_log_odds=round(b, 4),
                odds_ratio=round(math.exp(b), 3))
            for t, b in contribuciones[:3] if b > 0
        ]

        return Prediccion(
            probabilidad=round(prob, 5),
            probabilidad_pct=round(prob * 100, 2),
            categoria_riesgo=categoria,
            prevalencia_nacional=round(prev, 5),
            razon_sobre_prevalencia=round(razon, 2),
            factores_contribuyentes=factores,
        )

    @staticmethod
    def _etiqueta_categorica(termino: str) -> str:
        """Convierte ``grupo_etario_60+`` en ``Grupo etario: 60+``."""
        for prefijo, nombre in [("grupo_etario_", "Grupo etario"),
                                ("educacion_grupo_", "Nivel educativo"),
                                ("region_natural_", "Región natural")]:
            if termino.startswith(prefijo):
                return f"{nombre}: {termino[len(prefijo):]}"
        return termino

    def contexto(self) -> dict:
        """Carga el contexto epidemiológico precalculado.

        Son datos estáticos escritos por `preparar_datos_web.py`: la API de
        producción no tiene pandas para recalcularlos, y tampoco hace falta.
        """
        if getattr(self, "_contexto", None) is None:
            ruta = RUTA_DATOS / "contexto.json"
            self._contexto = (json.loads(ruta.read_text(encoding="utf-8"))
                              if ruta.exists() else {"departamentos": [], "nacional": {}})
        return self._contexto

    def departamento(self, codigo: str) -> dict | None:
        """Devuelve el contexto de un departamento por su código de dos dígitos."""
        for d in self.contexto().get("departamentos", []):
            if d["codigo"] == str(codigo).zfill(2):
                return d
        return None

    def _tasas(self) -> dict:
        """Carga el catálogo de tasas observadas por perfil."""
        if getattr(self, "_tasas_cache", None) is None:
            ruta = RUTA_DATOS / "tasas_observadas.json"
            self._tasas_cache = (json.loads(ruta.read_text(encoding="utf-8"))
                                 if ruta.exists() else {"tasas": {}, "_orden_niveles": []})
        return self._tasas_cache

    def tasa_observada(self, perfil) -> dict | None:
        """Busca la tasa realmente observada para un perfil en la ENDES.

        Baja por la escalera de niveles, del más específico al más general, y
        devuelve la primera celda que exista en el catálogo. El catálogo solo
        contiene celdas con suficientes casos, así que encontrar una es garantía
        de que la cifra se sostiene.

        Devuelve también ``definido_por``, para que la interfaz pueda decir a
        qué se parece exactamente el perfil en lugar de un vago «parecido».
        """
        cat = self._tasas()
        tasas = cat.get("tasas", {})
        valores = {
            "sexo": perfil.sexo.value if hasattr(perfil.sexo, "value") else str(perfil.sexo),
            "grupo_etario": (perfil.grupo_etario.value
                             if hasattr(perfil.grupo_etario, "value") else str(perfil.grupo_etario)),
            "educacion_grupo": (perfil.nivel_educativo.value
                                if hasattr(perfil.nivel_educativo, "value")
                                else str(perfil.nivel_educativo)),
            "area": perfil.area.value if hasattr(perfil.area, "value") else str(perfil.area),
            "region_natural": (perfil.region_natural.value
                               if hasattr(perfil.region_natural, "value")
                               else str(perfil.region_natural)),
        }
        for nivel in cat.get("_orden_niveles", []):
            clave = "|".join(valores[c] for c in nivel)
            if clave in tasas:
                return {**tasas[clave], "clave": clave}
        return None

    def info(self) -> dict:
        """Devuelve los metadatos del modelo para el endpoint ``/model-info``."""
        m = self.metadatos
        return {
            "tipo": "Regresión logística con diseño muestral complejo",
            "desenlace": "Sintomatología depresiva moderada o grave",
            "instrumento": "PHQ-9",
            "punto_de_corte": 10,
            "n_entrenamiento": int(m.get("n", 0)),
            "prevalencia": float(m.get("prevalencia", 0)),
            "auc": float(m.get("auc", 0)),
            "brier": float(m.get("brier", 0)),
            "variables": list(m.get("variables_modelo", [])),
            "fuente": "ENDES 2025 — Instituto Nacional de Estadística e Informática del Perú",
            "usos_prohibidos": USOS_PROHIBIDOS,
        }


servicio = Servicio()
