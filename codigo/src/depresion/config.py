"""Configuración central del proyecto.

Rutas, semilla, códigos de variables y constantes metodológicas.
Todo el proyecto lee de aquí: no debe haber rutas absolutas ni códigos
de variable dispersos por notebooks o scripts.

Notes
-----
Las decisiones metodológicas que llevan comentario ``JUSTIFICACIÓN`` se
sustentan en la auditoría previa documentada en ``HALLAZGOS_FASE_0.md``.
"""

from __future__ import annotations

import os
import unicodedata
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────
# 1. RUTAS
# ─────────────────────────────────────────────────────────────────────

# config.py -> depresion -> src -> codigo -> RAIZ
RAIZ = Path(__file__).resolve().parents[3]

DATOS = RAIZ / "datos"
DATOS_CRUDOS = DATOS / "crudos"
DATOS_INTERMEDIOS = DATOS / "intermedios"
DATOS_FINAL = DATOS / "final"
DATOS_EXTERNOS = DATOS / "externos"

RESULTADOS = RAIZ / "resultados"
TABLAS = RESULTADOS / "tablas"
FIGURAS = RESULTADOS / "figuras"
MAPAS = RESULTADOS / "mapas"
MODELOS = RESULTADOS / "modelos"
LOGS = RESULTADOS / "logs"

DOCS = RAIZ / "docs"
BOLETIN = RAIZ / "boletin"

# Fuente original de los microdatos. Están fuera del repositorio —pesan y son
# públicos del INEI— así que la ruta se configura por entorno:
#
#     export ENDES_SAV="/ruta/a/los/sav"        # Linux o Git Bash
#     $env:ENDES_SAV = "D:\datos\endes"         # PowerShell
#
# El valor por defecto es la ruta de la máquina donde se desarrolló, para que
# `make data` funcione ahí sin configurar nada. En cualquier otra hay que
# fijar la variable: sin ella, la construcción del dataset falla con un aviso
# claro en vez de con un FileNotFoundError sin contexto.
FUENTE_SAV = Path(os.getenv(
    "ENDES_SAV",
    RAIZ.parent / "DATA" / "DATASET FINAL - DEPRESION SALUD MENTAL",
))

ARCHIVO_CSALUD = "CSALUD01_2025.sav"
ARCHIVO_RECH0 = "RECH0_2025.sav"
ARCHIVO_RECH1 = "RECH1_2025.sav"

DATASET_FINAL = DATOS_FINAL / "data.parquet"

# ─────────────────────────────────────────────────────────────────────
# 2. REPRODUCIBILIDAD
# ─────────────────────────────────────────────────────────────────────

RANDOM_SEED = 42

# ─────────────────────────────────────────────────────────────────────
# 3. DISEÑO MUESTRAL COMPLEJO
# ─────────────────────────────────────────────────────────────────────
# Confirmado en FICHA_TECNICA_ENDES 2025.pdf, pág. 12:
#   "qhcluster: conglomerado, HV022: estrato, peso = PESO15_AMAS / 1000000"

VAR_PESO = "Peso15_AMAS"      # vive en CSALUD01
VAR_CONGLOMERADO = "QHCLUSTER"  # vive en CSALUD01
VAR_ESTRATO = "HV022"          # vive en RECH0 -> exige unir antes de declarar el diseño

ESCALA_PESO = 1_000_000

# JUSTIFICACIÓN: sum(Peso15_AMAS/1e6) = 36 172.81, del orden del tamaño
# muestral y NO de la población peruana de 15+ (~26 millones). Es un peso
# RELATIVO normalizado, no un factor de expansión.
#   -> Prevalencias, proporciones, medias, OR y errores estándar: válidos.
#   -> Totales poblacionales absolutos: NO son recuperables sin recalibrar
#      contra una proyección externa del INEI.
SUMA_PESOS_ESPERADA = 36_172.81
PESO_ES_FACTOR_EXPANSION = False

# ─────────────────────────────────────────────────────────────────────
# 4. LLAVE DE UNIÓN
# ─────────────────────────────────────────────────────────────────────

LLAVE = "HHID"
MATCH_MINIMO = 0.99  # si baja de aquí, el pipeline se detiene (§6 del prompt)

# ─────────────────────────────────────────────────────────────────────
# 5. DESENLACE — PHQ-9
# ─────────────────────────────────────────────────────────────────────

ITEMS_PHQ9 = [f"QS700{x}" for x in "ABCDEFGHI"]

ETIQUETAS_PHQ9 = {
    "QS700A": "Poco interés o placer en hacer las cosas",
    "QS700B": "Se sintió deprimido(a), decaído(a) o sin esperanza",
    "QS700C": "Problemas para dormir o dormir demasiado",
    "QS700D": "Se sintió cansado(a) o con poca energía",
    "QS700E": "Poco apetito o comer en exceso",
    "QS700F": "Dificultad para poner atención o concentrarse",
    "QS700G": "Moverse o hablar lento, o estar inquieto(a)",
    "QS700H": "Pensamientos de hacerse daño",  # ítem sensible, ver ÉTICA
    "QS700I": "Se sintió mal consigo mismo(a) o fracasado(a)",
}

# Escala de cada ítem (verificada en meta.variable_value_labels)
ESCALA_PHQ9 = {
    0: "Para nada",
    1: "Varios días (1 a 6 días)",
    2: "La mayoría de días (7 a 11 días)",
    3: "Casi todos los días (12 o más días)",
}

# ─────────────────────────────────────────────────────────────────────
# Umbral de publicación por precisión
# ─────────────────────────────────────────────────────────────────────
# Coeficiente de variación máximo para publicar una estimación sin
# advertencia. El 0,20 es la convención de las oficinas de estadística
# (INEI, Statistics Canada, ONS): por encima, el error estándar es tan
# grande respecto de la estimación que la cifra puntual no significa nada.
#
# La regla del proyecto es marcar, no suprimir. Una celda imprecisa que se
# borra deja un hueco que el lector rellena solo, casi siempre mal; una que
# se marca comunica a la vez el dato y su fragilidad. Ver la Puna en la
# tabla 33: CV 0,222, con un intervalo de 7,4 % a 18,0 %.
CV_MAXIMO_PUBLICABLE = 0.20

NOTA_CV_ALTO = (
    "Estimación imprecisa (CV > 0,20): la muestra de esta categoría es pequeña. "
    "Debe leerse por su intervalo de confianza, no por la cifra puntual.")

CORTE_DEPRESION = 10        # ★ desenlace principal: moderada o más
CORTE_DEPRESION_LEVE = 5    # análisis de sensibilidad

CATEGORIAS_PHQ9 = [
    (0, 4, "Mínima"),
    (5, 9, "Leve"),
    (10, 14, "Moderada"),
    (15, 19, "Moderadamente severa"),
    (20, 27, "Severa"),
]

# ÉTICA (§15.3): QS700H entra en el puntaje porque forma parte del
# instrumento, pero NO se analiza ni se destaca como desenlace independiente.
ITEM_SENSIBLE = "QS700H"

# ─────────────────────────────────────────────────────────────────────
# 6. VARIABLES PROHIBIDAS COMO PREDICTORES  (fuga de información)
# ─────────────────────────────────────────────────────────────────────
# JUSTIFICACIÓN (HALLAZGOS_FASE_0.md §2.2):
#   QS702  se pregunta EXACTAMENTE a quien marcó >=1 síntoma en QS700.
#          Su cobertura (49.46 %) es idéntica al % con phq9_score > 0.
#          La cobertura *es* el desenlace disfrazado.
#   QS703  es un tamizaje de síntomas depresivos de 12 meses: proxy directo.
#   QS704* cuelgan de QS703 -> heredan la fuga.
# Pueden usarse como DESCRIPTIVOS o en análisis de sensibilidad, nunca
# como predictores de depresion_bin.

VARIABLES_CON_FUGA = ["QS702", "QS703"] + [f"QS704{x}" for x in "ABCDEFGHI"]

# ─────────────────────────────────────────────────────────────────────
# 7. EXPOSICIONES
# ─────────────────────────────────────────────────────────────────────

# Alcohol. Cadena verificada en el cuestionario:
#   QS206 (alguna vez) -> QS208 (12 meses) -> QS209 (>=12 días) -> QS713-717
#   -> [si alguna == Sí] -> QS719-729
# JUSTIFICACIÓN: el prompt indicaba que el bloque de dependencia colgaba de
# QS209/QS210. El cuestionario dice "VERIFIQUE PREGUNTA 209: RESPONDIÓ SÍ
# (CÓDIGO 1)" -> cuelga SOLO de QS209, y en DOS niveles anidados.
VAR_ALCOHOL_ALGUNA_VEZ = "QS206"
VAR_ALCOHOL_12M = "QS208"
VAR_ALCOHOL_FRECUENTE = "QS209"   # >= 12 días en 12 meses
VAR_ALCOHOL_30D = "QS210"

# Nivel 1 de dependencia (n=3 197, filtro QS209==1)
ITEMS_DEPENDENCIA_N1 = ["QS713", "QS714", "QS715", "QS716", "QS717"]
# Nivel 2 de severidad (n=951, filtro: alguna de N1 == Sí)
ITEMS_DEPENDENCIA_N2 = [
    "QS719", "QS720", "QS721", "QS722", "QS723",
    "QS724", "QS725", "QS726", "QS727", "QS728", "QS729",
]

# Tabaco: QS200 (12m) -> QS201 (30d) -> QS202 (diario)
VAR_TABACO_12M = "QS200"
VAR_TABACO_30D = "QS201"
VAR_TABACO_DIARIO = "QS202"

# Violencia de pareja: QS709 (tuvo pareja) -> QS710, QS711
VAR_TUVO_PAREJA = "QS709"
VAR_VIOLENCIA_GOLPE = "QS710"   # con mano/pie/puño
VAR_VIOLENCIA_OBJETO = "QS711"  # con objeto (correa, palo…)

# ⚠ QS711: el diccionario SPSS etiqueta los códigos 1, 2, 8 y 9, pero en los
# datos aparecen 1, 2, 3 y 4 (33 casos en 3 y 4, sin etiqueta). Es un error de
# etiquetado del INEI: la variable está grabada en la MISMA escala 1-4 que su
# pregunta gemela QS710. Se recodifica explícitamente y se documenta.
ESCALA_VIOLENCIA = {
    1: "Nunca",
    2: "Rara vez (1-2 veces)",
    3: "A veces (3-5 veces)",
    4: "A menudo (6 o más veces)",
}
QS711_ETIQUETAS_INEI_ERRONEAS = {1: 1, 2: 2, 8: 3, 9: 4}

# Clínicas
VAR_HTA_DX = "QS102"
VAR_DIABETES_DX = "QS109"
VAR_PESO_KG = "QS900"
VAR_TALLA_CM = "QS901"
VAR_PERIMETRO_ABD = "QS907"
PRESION_SISTOLICA = ["QS903S", "QS905S"]
PRESION_DIASTOLICA = ["QS903D", "QS905D"]

# Variables de "resultado de la medición" (vía limpia para excluir no-medidos)
VAR_RESULTADO_ANTROPOMETRIA = "QS902"
VAR_RESULTADO_PRESION = "QS906"
VAR_RESULTADO_PERIMETRO = "QS908"
CODIGO_MEDIDO = 1

# Códigos de no-medición: 999.9 en QS900/QS901/QS907.
# ⚠ NO aplicar a la presión arterial: sus rangos son plausibles
# (sistólica 61-220, diastólica 40-142) y el faltante es NaN directo.
UMBRAL_NO_MEDICION = 900

# Puntos de corte clínicos
IMC_OBESIDAD = 30.0
IMC_SOBREPESO = 25.0
HTA_SISTOLICA = 140
HTA_DIASTOLICA = 90
PERIMETRO_RIESGO = {1: 102, 2: 88}  # 1=Hombre (cm), 2=Mujer (cm)

# Atención en salud mental
VAR_TRATAMIENTO_SM = "QS707"
PREFIJO_LUGAR_ATENCION = "QS708_"

# ─────────────────────────────────────────────────────────────────────
# 8. SOCIODEMOGRÁFICAS
# ─────────────────────────────────────────────────────────────────────

VAR_EDAD = "QS23"          # 15-97; 97 = "97 o más años"
EDAD_TOPE = 97
VAR_SEXO = "QSSEXO"        # 1=Hombre, 2=Mujer
VAR_EDUCACION = "QS25N"    # 0=Inicial … 5=Postgrado
VAR_RESULTADO_ENTREVISTA = "QSRESULT"

# Geográficas (viven en RECH0)
VAR_DEPARTAMENTO = "HV024"  # etiquetas limpias (HV023 las trae con espacios)
VAR_DOMINIO = "HV023"       # idéntica a HV024 fila a fila (100 %)
VAR_AREA = "HV025"          # 1=Urbano, 2=Rural
VAR_ALTITUD = "HV040"       # altitud del conglomerado, en metros
VAR_UBIGEO = "UBIGEO"
VAR_LONGITUD = "LONGITUDX"
VAR_LATITUD = "LATITUDY"
VAR_CENTRO_POBLADO = "NOMCCPP"

# Shapefiles oficiales del INEI 2023 (geogpsperu / SuyoPomalia), ya en EPSG:4326.
SHAPEFILES = DATOS_EXTERNOS / "shapefiles"
GEOJSON_WEB = DATOS_EXTERNOS / "geojson"

GRUPOS_ETARIOS = [
    (15, 19, "15-19"),
    (20, 29, "20-29"),
    (30, 39, "30-39"),
    (40, 49, "40-49"),
    (50, 59, "50-59"),
    (60, 200, "60+"),
]

# ─────────────────────────────────────────────────────────────────────
# 9. REGIÓN NATURAL — variable derivada
# ─────────────────────────────────────────────────────────────────────
# JUSTIFICACIÓN: ENDES no trae región natural. El prompt proponía un mapeo
# departamento -> región, pero la altitud es FUERTEMENTE bimodal dentro de
# varios departamentos (Áncash: 42 % <500 m y 55 % >2300 m; La Libertad
# 70 %/25 %; Arequipa 10 %/72 %). Un mapeo por departamento clasificaría mal
# a miles de hogares.
#
# Regla adoptada, aplicada a nivel de CONGLOMERADO:
#   1) Sierra  si altitud (HV040) >= 1500 m
#   2) Costa   si no, y el departamento está en la vertiente occidental
#   3) Selva   en cualquier otro caso
#
# Validación: reproduce correctamente los casos conocidos —Loreto, Ucayali y
# San Martín 100 % selva; Tumbes y Callao 100 % costa; Huancavelica y
# Apurímac 100 % sierra; y recupera la selva alta de Cajamarca (Jaén),
# Junín (Chanchamayo), Cusco (La Convención) y Puno (Sandia).

ALTITUD_SIERRA = 1500

DEPARTAMENTOS_VERTIENTE_OCCIDENTAL = {
    "Tumbes", "Piura", "Lambayeque", "La Libertad", "Ancash",
    "Lima", "Callao", "Ica", "Arequipa", "Moquegua", "Tacna",
}

REGIONES_NATURALES = ["Costa", "Sierra", "Selva"]

# Dominio INEI de 4 categorías (Lima Metropolitana = prov. Lima + prov. Callao)
UBIGEO_LIMA_METROPOLITANA = {"1501", "0701"}

# ─────────────────────────────────────────────────────────────────────
# 10. TEMA GRÁFICO
# ─────────────────────────────────────────────────────────────────────

# Los nombres de las claves se conservan por compatibilidad con el código que
# ya las usa, pero los valores son los de la identidad de salud mental definida
# en `diseno.py`: verde-teal del lazo de la salud mental como voz principal,
# neutros de base tierra en lugar de grises azulados, y terracota en vez de rojo
# de alarma. Si se cambia algo aquí, cambiarlo también allí.
COLORES = {
    "navy": "#12352F",          # verde-900: el color de los titulares
    "navy_claro": "#236158",    # verde-700: color de marca
    "dorado": "#C4714E",        # arcilla-500: el acento cálido
    "dorado_claro": "#DFA98F",  # arcilla-300
    "rojo": "#9C3A50",          # ciruela-500: serio, no estridente
    "verde": "#2F7D71",         # verde-600: protector
    "ambar": "#D2A03C",         # miel-500: destacado
    "gris": "#6E675E",          # tierra-500: neutro cálido
    "gris_claro": "#D8D2C7",    # tierra-200
    "fondo": "#FFFDFA",         # blanco cálido, no puro
}

PALETA_SECUENCIAL = ["#EAF3F0", "#C4DFD8", "#94C4B9", "#5FA396", "#357F73", "#1A5A50", "#12352F"]
PALETA_CATEGORICA = [
    COLORES["navy_claro"], COLORES["dorado"], COLORES["ambar"],
    "#5A6B58", "#8FBDB4", COLORES["gris"],
]

DPI_FIGURAS = 300
FORMATOS_TABLA = ("csv", "xlsx", "tex")
FORMATOS_FIGURA = ("png", "pdf", "html")

# ─────────────────────────────────────────────────────────────────────
# 11. TEXTOS OBLIGATORIOS (ética, §15)
# ─────────────────────────────────────────────────────────────────────

DISCLAIMER = (
    "Esta herramienta estima riesgo epidemiológico con fines académicos y de "
    "salud pública. No constituye un diagnóstico médico ni reemplaza la "
    "evaluación de un profesional de salud mental."
)

LINEA_AYUDA = (
    "Si te sientes mal, busca ayuda profesional. En el Perú puedes llamar "
    "gratuitamente a la Línea 113, opción 5 (salud mental), del MINSA."
)

# ─────────────────────────────────────────────────────────────────────
# 12. UTILIDADES
# ─────────────────────────────────────────────────────────────────────


def normalizar_texto(s: str) -> str:
    """Quita tildes, espacios sobrantes y pasa a mayúsculas.

    Se usa para cruzar nombres de departamento con el GeoJSON: las etiquetas
    de ENDES vienen sin tildes pero con espacios a la izquierda en HV023.

    Parameters
    ----------
    s : str
        Texto a normalizar.

    Returns
    -------
    str
        Texto sin tildes, sin espacios en los extremos y en mayúsculas.

    Examples
    --------
    >>> normalizar_texto("  Huánuco ")
    'HUANUCO'
    """
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().upper()


def crear_directorios() -> None:
    """Crea todos los directorios de salida si no existen."""
    for d in (
        DATOS_CRUDOS, DATOS_INTERMEDIOS, DATOS_FINAL, DATOS_EXTERNOS,
        TABLAS, FIGURAS, MAPAS, MODELOS, LOGS, DOCS,
    ):
        d.mkdir(parents=True, exist_ok=True)
