"""Georreferenciación: coordenadas, UBIGEO, altitud y límites del INEI.

Tres cosas que la primera corrida dejó sin aprovechar y que aquí se incorporan:

1. **Las coordenadas del centro poblado**, que traen 1 327 hogares (3,55 %) con
   los campos de latitud y longitud intercambiados.
2. **El UBIGEO**, que identifica departamento, provincia y distrito y permite
   cruzar con los límites oficiales.
3. **La altitud del conglomerado** (`HV040`), que abre una línea de análisis
   propia.

Los shapefiles del INEI 2023 ya vienen en EPSG:4326, de modo que no hay que
reproyectar para los mapas web.
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as cfg
from .variables import _regla

log = logging.getLogger(__name__)
warnings.filterwarnings("ignore", message=".*Shapely 2.*")

# Las variables que se construyen aquí se registran en la misma bitácora que
# las de variables.py. Sin esto salían al diccionario con la regla en blanco:
# el generador lee REGLAS y lo que no esté ahí aparece sin documentar, en
# silencio y sin que ningún test lo note.
_regla("ubigeo", "Código INEI de seis dígitos, rellenado con ceros a la izquierda.")
_regla("cod_departamento", "Dígitos 1-2 del UBIGEO. 25 unidades: 24 departamentos "
                           "más la Provincia Constitucional del Callao.")
_regla("cod_provincia", "Dígitos 1-4 del UBIGEO. Acumulativo: el código de provincia "
                        "solo es único dentro de su departamento.")
_regla("cod_distrito", "UBIGEO completo de seis dígitos, único a nivel nacional.")
_regla("longitud", "LONGITUDX del centro poblado, tras corregir los registros con "
                   "los campos intercambiados. NaN si el punto cae fuera del Perú.")
_regla("latitud", "LATITUDY del centro poblado, con la misma corrección que longitud.")
_regla("coord_estado", "Trazabilidad de la corrección: correcta / corregida (campos "
                       "intercambiados) / descartada (fuera del territorio) / sin dato.")
_regla("NOMCCPP", "Nombre del centro poblado, tal como viene en RECH0. No se usa en "
                  "el análisis; se conserva para poder auditar casos concretos.")
_regla("altitud", "HV040, altitud del conglomerado en metros sobre el nivel del mar.")
_regla("altitud_categoria", "Piso altitudinal de Pulgar Vidal: Costa/selva baja "
                            "(0-499), Yunga (500-1 999), Quechua (2 000-2 999), "
                            "Suni (3 000-3 999), Puna (4 000+). Ordinal.")
_regla("altitud_100m", "altitud / 100. El OR por metro sería ilegible (1,0001).")
_regla("altitud_km", "altitud / 1000, para los modelos que reportan por kilómetro.")
_regla("gran_altitud", "1 si altitud >= 2 500 m. El corte es el de la literatura "
                       "sobre altitud y depresión, no un cuantil de esta muestra.")

# ── Rangos válidos del territorio peruano ─────────────────────────────
# Tomados del bounding box de los shapefiles oficiales del INEI 2023, con un
# margen de holgura para no descartar puntos legítimamente fronterizos.
LONGITUD_PERU = (-81.4, -68.6)
LATITUD_PERU = (-18.4, 0.0)

RUTA_SHAPEFILES = cfg.DATOS_EXTERNOS / "shapefiles"
NIVELES = {"departamental": "CCDD", "provincial": "CCPP", "distrital": "UBIGEO"}


# ─────────────────────────────────────────────────────────────────────
# 1. Coordenadas
# ─────────────────────────────────────────────────────────────────────


def corregir_coordenadas(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Corrige los registros con latitud y longitud intercambiadas.

    Regla: si un par de coordenadas cae fuera del territorio peruano pero al
    intercambiar los campos queda dentro, se intercambia. Si sigue fuera tras
    intercambiar, se marca como faltante — es preferible perder un punto que
    situarlo en el océano.

    Parameters
    ----------
    df : pandas.DataFrame
        Debe contener ``LONGITUDX`` y ``LATITUDY``.

    Returns
    -------
    tuple of (pandas.DataFrame, pandas.DataFrame)
        El DataFrame con ``longitud``, ``latitud`` y ``coord_estado``, y la
        bitácora con el recuento de cada grupo.
    """
    out = df.copy()
    lon = pd.to_numeric(out["LONGITUDX"], errors="coerce")
    lat = pd.to_numeric(out["LATITUDY"], errors="coerce")

    correcto = lon.between(*LONGITUD_PERU) & lat.between(*LATITUD_PERU)
    invertido = lat.between(*LONGITUD_PERU) & lon.between(*LATITUD_PERU) & ~correcto
    descartado = ~correcto & ~invertido

    out["longitud"] = np.where(invertido, lat, lon)
    out["latitud"] = np.where(invertido, lon, lat)
    out.loc[descartado, ["longitud", "latitud"]] = np.nan
    out["coord_estado"] = np.select(
        [correcto, invertido, descartado],
        ["correcta", "corregida (campos intercambiados)", "descartada (fuera del territorio)"],
        default="sin dato")

    bitacora = pd.DataFrame([
        {"grupo": "Correctas", "n": int(correcto.sum()),
         "pct": round(correcto.mean() * 100, 2),
         "accion": "Se usan tal cual"},
        {"grupo": "Intercambiadas", "n": int(invertido.sum()),
         "pct": round(invertido.mean() * 100, 2),
         "accion": "Se intercambian los campos LONGITUDX y LATITUDY"},
        {"grupo": "Fuera de rango", "n": int(descartado.sum()),
         "pct": round(descartado.mean() * 100, 2),
         "accion": "Se marcan como faltantes"},
    ])
    log.info("Coordenadas: %s correctas, %s corregidas, %s descartadas",
             f"{int(correcto.sum()):,}", f"{int(invertido.sum()):,}",
             f"{int(descartado.sum()):,}")
    return out, bitacora


def validar_contra_distrito(df: pd.DataFrame, muestra: int | None = 4000) -> dict:
    """Comprueba que las coordenadas caigan dentro del distrito que declara el UBIGEO.

    Es la verificación que de verdad prueba que la corrección funcionó: un punto
    puede estar dentro del territorio peruano y aun así en el departamento
    equivocado. Se hace sobre una muestra porque el cruce espacial completo es
    costoso y con unos miles de puntos ya se ve si hay un problema sistemático.

    Returns
    -------
    dict
        Recuento de coincidencias, discrepancias y su porcentaje.
    """
    import geopandas as gpd
    from shapely.geometry import Point

    d = df.dropna(subset=["longitud", "latitud"]).copy()
    d["ubigeo6"] = d[cfg.VAR_UBIGEO].astype(str).str.zfill(6)
    if muestra and len(d) > muestra:
        d = d.sample(muestra, random_state=cfg.RANDOM_SEED)

    distritos = cargar_limites("distrital")[["UBIGEO", "geometry"]]
    puntos = gpd.GeoDataFrame(
        d[["ubigeo6"]],
        geometry=[Point(xy) for xy in zip(d.longitud, d.latitud, strict=True)],
        crs="EPSG:4326")

    cruce = gpd.sjoin(puntos, distritos, how="left", predicate="within")
    cruce = cruce[~cruce.index.duplicated(keep="first")]
    coincide = (cruce["UBIGEO"] == cruce["ubigeo6"]).sum()
    sin_poligono = cruce["UBIGEO"].isna().sum()

    return {
        "n_evaluados": len(cruce),
        "coinciden": int(coincide),
        "pct_coinciden": round(coincide / len(cruce) * 100, 2),
        "en_otro_distrito": int(len(cruce) - coincide - sin_poligono),
        "sin_poligono": int(sin_poligono),
        "veredicto": (
            "La corrección es coherente con el UBIGEO declarado"
            if coincide / len(cruce) > 0.90 else
            "Discrepancia alta: revisar la corrección de coordenadas"),
    }


# ─────────────────────────────────────────────────────────────────────
# 2. UBIGEO
# ─────────────────────────────────────────────────────────────────────


def descomponer_ubigeo(df: pd.DataFrame) -> pd.DataFrame:
    """Separa el UBIGEO en sus tres niveles administrativos.

    El código de seis dígitos se lee así: 1-2 departamento, 3-4 provincia,
    5-6 distrito. Los códigos de provincia y distrito **solo son únicos dentro
    de su nivel superior**, así que se construyen acumulativos.
    """
    out = df.copy()
    u = out[cfg.VAR_UBIGEO].astype(str).str.zfill(6)
    out["ubigeo"] = u
    out["cod_departamento"] = u.str[:2]
    out["cod_provincia"] = u.str[:4]
    out["cod_distrito"] = u
    log.info("UBIGEO: %s departamentos, %s provincias, %s distritos",
             out.cod_departamento.nunique(), out.cod_provincia.nunique(),
             out.cod_distrito.nunique())
    return out


# ─────────────────────────────────────────────────────────────────────
# 3. Altitud
# ─────────────────────────────────────────────────────────────────────

#: Pisos altitudinales según la clasificación de Javier Pulgar Vidal, que es la
#: referencia habitual en geografía peruana. Se prefiere a los cuartiles porque
#: tiene significado sustantivo: cada piso implica un ecosistema, una economía y
#: una forma de vida distintas.
PISOS_ALTITUDINALES = [
    (0, 500, "Costa / selva baja (0-499 m)"),
    (500, 2000, "Yunga (500-1 999 m)"),
    (2000, 3000, "Quechua (2 000-2 999 m)"),
    (3000, 4000, "Suni (3 000-3 999 m)"),
    (4000, 10000, "Puna (4 000 m o más)"),
]

ORDEN_PISOS = [e for _, _, e in PISOS_ALTITUDINALES]


def construir_altitud(df: pd.DataFrame) -> pd.DataFrame:
    """Construye la altitud y su categorización por pisos altitudinales."""
    out = df.copy()
    out["altitud"] = pd.to_numeric(out[cfg.VAR_ALTITUD], errors="coerce")

    cats = pd.Series(pd.NA, index=out.index, dtype="object")
    for lo, hi, etq in PISOS_ALTITUDINALES:
        cats[(out.altitud >= lo) & (out.altitud < hi)] = etq
    out["altitud_categoria"] = pd.Categorical(cats, categories=ORDEN_PISOS, ordered=True)

    # Versión en cientos de metros: el OR por metro sería ilegible (1,0001).
    out["altitud_100m"] = out.altitud / 100
    out["altitud_km"] = out.altitud / 1000
    out["gran_altitud"] = (out.altitud >= 2500).astype("Float64").where(out.altitud.notna())

    log.info("Altitud: mediana %.0f m, rango %.0f-%.0f m",
             out.altitud.median(), out.altitud.min(), out.altitud.max())
    return out


# ─────────────────────────────────────────────────────────────────────
# 4. Límites administrativos
# ─────────────────────────────────────────────────────────────────────


def cargar_limites(nivel: str = "departamental"):
    """Carga el shapefile del INEI 2023 del nivel indicado.

    Parameters
    ----------
    nivel : {"departamental", "provincial", "distrital"}

    Returns
    -------
    geopandas.GeoDataFrame
        Geometrías en EPSG:4326, listas para mapas web.

    Raises
    ------
    FileNotFoundError
        Si el shapefile no está descomprimido.
    """
    import geopandas as gpd

    carpeta = RUTA_SHAPEFILES / nivel
    archivos = list(carpeta.glob("*.shp"))
    if not archivos:
        raise FileNotFoundError(
            f"No hay shapefile en {carpeta}. Ejecuta `python codigo/scripts/preparar_geo.py`.")
    g = gpd.read_file(archivos[0])
    if g.crs is None:
        g = g.set_crs("EPSG:4326")
    elif g.crs.to_epsg() != 4326:
        log.info("Reproyectando %s de %s a EPSG:4326", nivel, g.crs)
        g = g.to_crs("EPSG:4326")

    if nivel == "provincial" and "CCPP" in g.columns:
        # El código de provincia solo es único dentro de su departamento.
        g["cod_provincia"] = g.CCDD.astype(str).str.zfill(2) + g.CCPP.astype(str).str.zfill(2)
    if nivel == "departamental":
        g["cod_departamento"] = g.CCDD.astype(str).str.zfill(2)
    return g


def simplificar_para_web(g, tolerancia: float = 0.01):
    """Simplifica las geometrías para que el GeoJSON del navegador sea ligero.

    Los límites distritales completos pesan decenas de megabytes, que ningún
    boletín debería descargar. A esta tolerancia la forma sigue siendo
    reconocible a escala nacional.
    """
    out = g.copy()
    out["geometry"] = out.geometry.simplify(tolerancia, preserve_topology=True)
    return out


def exportar_geojson(g, destino: Path, tolerancia: float | None = 0.01) -> dict:
    """Exporta un GeoDataFrame a GeoJSON, simplificado si se pide."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    salida = simplificar_para_web(g, tolerancia) if tolerancia else g
    salida.to_file(destino, driver="GeoJSON")
    peso = destino.stat().st_size / 1e6
    log.info("GeoJSON escrito: %s (%.2f MB, %s geometrías)", destino.name, peso, len(salida))
    return {"archivo": destino.name, "mb": round(peso, 2), "n": len(salida)}


# ─────────────────────────────────────────────────────────────────────
# 5. Agregación con salvaguarda de muestra mínima
# ─────────────────────────────────────────────────────────────────────

#: Por debajo de este número de personas, una estimación territorial no se
#: publica: el intervalo sería tan ancho que el mapa engañaría más de lo que
#: informa.
N_MINIMO_TERRITORIAL = 50


def agregar_por_territorio(
    df: pd.DataFrame, codigo: str, variable: str = "depresion_bin",
    n_minimo: int = N_MINIMO_TERRITORIAL,
) -> pd.DataFrame:
    """Agrega una prevalencia ponderada por unidad territorial.

    Marca como no estimables las unidades que no alcanzan el tamaño mínimo, en
    lugar de publicar una cifra que el mapa presentaría con la misma autoridad
    visual que las demás.

    Returns
    -------
    pandas.DataFrame
        Una fila por territorio con n, prevalencia ponderada y ``estimable``.
    """
    d = df.dropna(subset=[variable, codigo]).copy()
    filas = []
    for cod, g in d.groupby(codigo):
        n = len(g)
        w = g.peso if "peso" in g else pd.Series(1.0, index=g.index)
        prev = float(np.average(g[variable], weights=w)) * 100 if w.sum() > 0 else np.nan
        filas.append({
            codigo: cod, "n": n, "eventos": int(g[variable].sum()),
            "prevalencia": prev, "estimable": n >= n_minimo,
        })
    out = pd.DataFrame(filas)
    out.loc[~out.estimable, "prevalencia"] = np.nan
    log.info("Agregación por %s: %s territorios, %s estimables (n >= %s)",
             codigo, len(out), int(out.estimable.sum()), n_minimo)
    return out
