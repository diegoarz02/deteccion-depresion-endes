"""Entrada/salida: lectura de los .sav y guardado de tablas y figuras.

Toda tabla se guarda en csv + xlsx + tex; toda figura en png (300 dpi) + pdf,
y en html si es de Plotly. Nunca se deja un resultado solo en pantalla.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import pyreadstat

from . import config as cfg

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Metadatos
# ─────────────────────────────────────────────────────────────────────


@dataclass
class Metadatos:
    """Metadatos de un archivo SPSS, en forma manejable.

    Attributes
    ----------
    etiquetas_variable : dict
        Nombre de variable -> etiqueta descriptiva.
    etiquetas_valor : dict
        Nombre de variable -> {código: etiqueta}.
    medida : dict
        Nombre de variable -> nivel de medida declarado por SPSS.
    """

    etiquetas_variable: dict[str, str] = field(default_factory=dict)
    etiquetas_valor: dict[str, dict] = field(default_factory=dict)
    medida: dict[str, str] = field(default_factory=dict)

    def etiqueta(self, var: str) -> str:
        """Devuelve la etiqueta descriptiva de ``var`` (o el nombre si no hay)."""
        return self.etiquetas_variable.get(var, var)

    def valores(self, var: str) -> dict:
        """Devuelve el diccionario de códigos->etiqueta de ``var``."""
        return self.etiquetas_valor.get(var, {})

    def combinar(self, otro: Metadatos) -> Metadatos:
        """Une dos juegos de metadatos (para el resultado de un join)."""
        return Metadatos(
            {**self.etiquetas_variable, **otro.etiquetas_variable},
            {**self.etiquetas_valor, **otro.etiquetas_valor},
            {**self.medida, **otro.medida},
        )


def leer_sav(nombre: str, carpeta: Path | None = None) -> tuple[pd.DataFrame, Metadatos]:
    """Lee un archivo .sav conservando los códigos numéricos originales.

    Se lee con ``apply_value_formats=False`` deliberadamente: aplicar las
    etiquetas destruiría los 33 casos de violencia severa de QS711, cuya
    codificación real (3, 4) no coincide con el diccionario del INEI (8, 9).

    Parameters
    ----------
    nombre : str
        Nombre del archivo, p. ej. ``"CSALUD01_2025.sav"``.
    carpeta : Path, optional
        Carpeta donde buscarlo. Por defecto, la fuente original del INEI.

    Returns
    -------
    tuple of (pandas.DataFrame, Metadatos)
    """
    ruta = (carpeta or cfg.FUENTE_SAV) / nombre
    log.info("Leyendo %s", ruta)
    df, meta = pyreadstat.read_sav(str(ruta), apply_value_formats=False)
    md = Metadatos(
        etiquetas_variable=dict(zip(meta.column_names, meta.column_labels, strict=False)),
        etiquetas_valor=meta.variable_value_labels,
        medida=meta.variable_measure,
    )
    log.info("  %s: %s filas x %s columnas", nombre, f"{len(df):,}", df.shape[1])
    return df, md


# ─────────────────────────────────────────────────────────────────────
# Guardado de tablas
# ─────────────────────────────────────────────────────────────────────


def guardar_tabla(
    df: pd.DataFrame,
    nombre: str,
    titulo: str = "",
    carpeta: Path | None = None,
    indice: bool = False,
    decimales: int = 3,
) -> dict[str, Path]:
    """Guarda una tabla en csv, xlsx y tex (booktabs).

    Parameters
    ----------
    df : pandas.DataFrame
        Tabla a guardar.
    nombre : str
        Nombre base sin extensión, p. ej. ``"tabla_01_calidad_datos"``.
    titulo : str, optional
        Caption para la versión LaTeX.
    carpeta : Path, optional
        Destino. Por defecto ``resultados/tablas``.
    indice : bool, default False
        Si se escribe el índice del DataFrame.
    decimales : int, default 3
        Redondeo de las columnas numéricas.

    Returns
    -------
    dict
        Formato -> ruta del archivo escrito.
    """
    carpeta = carpeta or cfg.TABLAS
    carpeta.mkdir(parents=True, exist_ok=True)
    salidas: dict[str, Path] = {}

    df_out = df.copy()
    for c in df_out.select_dtypes("number").columns:
        df_out[c] = df_out[c].round(decimales)

    p = carpeta / f"{nombre}.csv"
    df_out.to_csv(p, index=indice, encoding="utf-8-sig")
    salidas["csv"] = p

    p = carpeta / f"{nombre}.xlsx"
    df_out.to_excel(p, index=indice, sheet_name=nombre[:31])
    salidas["xlsx"] = p

    p = carpeta / f"{nombre}.tex"
    tex = df_out.to_latex(
        index=indice,
        escape=True,
        longtable=len(df_out) > 40,
        caption=titulo or nombre.replace("_", " "),
        label=f"tab:{nombre}",
        position="htbp" if len(df_out) <= 40 else None,
    )
    # booktabs: to_latex ya emite toprule/midrule/bottomrule con estilo por defecto
    p.write_text(tex, encoding="utf-8")
    salidas["tex"] = p

    log.info("Tabla guardada: %s (%s filas) -> %s", nombre, len(df_out), list(salidas))
    return salidas


def guardar_figura(fig, nombre: str, carpeta: Path | None = None) -> dict[str, Path]:
    """Guarda una figura de matplotlib o de Plotly en todos los formatos.

    Parameters
    ----------
    fig : matplotlib.figure.Figure or plotly.graph_objects.Figure
        Figura a guardar.
    nombre : str
        Nombre base sin extensión, p. ej. ``"fig_01_distribucion_phq9"``.
    carpeta : Path, optional
        Destino. Por defecto ``resultados/figuras``.

    Returns
    -------
    dict
        Formato -> ruta del archivo escrito.
    """
    carpeta = carpeta or cfg.FIGURAS
    carpeta.mkdir(parents=True, exist_ok=True)
    salidas: dict[str, Path] = {}

    if hasattr(fig, "write_html"):  # Plotly
        p = carpeta / f"{nombre}.html"
        fig.write_html(p, include_plotlyjs="cdn", full_html=True)
        salidas["html"] = p
        for ext in ("png", "pdf"):
            try:
                p = carpeta / f"{nombre}.{ext}"
                fig.write_image(p, scale=3 if ext == "png" else 1)
                salidas[ext] = p
            except Exception as e:  # kaleido ausente o fallo de render
                log.warning("No se pudo exportar %s.%s: %s", nombre, ext, e)
    else:  # matplotlib
        for ext in ("png", "pdf"):
            p = carpeta / f"{nombre}.{ext}"
            fig.savefig(p, dpi=cfg.DPI_FIGURAS, bbox_inches="tight")
            salidas[ext] = p

    log.info("Figura guardada: %s -> %s", nombre, list(salidas))
    return salidas


# ─────────────────────────────────────────────────────────────────────
# Dataset final
# ─────────────────────────────────────────────────────────────────────


def hash_dataframe(df: pd.DataFrame) -> str:
    """Calcula el SHA-256 del contenido de un DataFrame.

    Se usa para versionar el dataset: dos ejecuciones del pipeline sobre los
    mismos insumos deben producir el mismo hash.
    """
    h = hashlib.sha256()
    h.update(",".join(df.columns).encode())
    h.update(pd.util.hash_pandas_object(df, index=True).values.tobytes())
    return h.hexdigest()


def guardar_dataset_final(df: pd.DataFrame, etiquetas: dict) -> dict[str, Path]:
    """Guarda el dataset único en parquet, csv, y sus etiquetas y hash.

    Parameters
    ----------
    df : pandas.DataFrame
        Dataset analítico final.
    etiquetas : dict
        Diccionario de etiquetas de variables y categorías.

    Returns
    -------
    dict
        Nombre lógico -> ruta escrita.
    """
    cfg.DATOS_FINAL.mkdir(parents=True, exist_ok=True)
    salidas = {}

    p = cfg.DATOS_FINAL / "data.parquet"
    df.to_parquet(p, index=False)
    salidas["parquet"] = p

    p = cfg.DATOS_FINAL / "data.csv"
    df.to_csv(p, index=False, encoding="utf-8-sig")
    salidas["csv"] = p

    p = cfg.DATOS_FINAL / "data_labels.json"
    p.write_text(json.dumps(etiquetas, ensure_ascii=False, indent=2), encoding="utf-8")
    salidas["labels"] = p

    digest = hash_dataframe(df)
    p = cfg.DATOS_FINAL / "data_hash.txt"
    p.write_text(
        f"sha256  {digest}\nfilas   {len(df)}\ncolumnas {df.shape[1]}\n",
        encoding="utf-8",
    )
    salidas["hash"] = p

    log.info("Dataset final: %s filas x %s cols, sha256=%s…",
             f"{len(df):,}", df.shape[1], digest[:12])
    return salidas


def configurar_logging(nivel: str = "INFO") -> None:
    """Configura logging a consola y a ``resultados/logs/ejecucion.log``."""
    cfg.LOGS.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, nivel.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)-22s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(cfg.LOGS / "ejecucion.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )
