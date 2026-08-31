"""Tema gráfico único del proyecto.

Paleta navy / dorado con acentos rojo, verde y ámbar. Separador decimal con
punto. Aplicar ``aplicar_tema()`` una vez al inicio de cada notebook o script
para que todas las figuras salgan iguales.
"""

from __future__ import annotations

import matplotlib as mpl

# Backend no interactivo, fijado ANTES de importar pyplot.
#
# Los scripts de este proyecto solo guardan figuras a disco: no abren ventanas.
# Con el backend interactivo por defecto (TkAgg en Windows), el intérprete
# termina lanzando "RuntimeError: main thread is not in main loop" al cerrar, y
# el script sale con código distinto de cero aunque haya hecho su trabajo. Eso
# rompe `make` y cualquier integración continua.
mpl.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

from . import config as cfg  # noqa: E402

C = cfg.COLORES


def aplicar_tema() -> None:
    """Fija el estilo de matplotlib para todo el proyecto."""
    mpl.rcParams.update({
        "figure.figsize": (9, 5.5),
        "figure.dpi": 110,
        "savefig.dpi": cfg.DPI_FIGURAS,
        "savefig.bbox": "tight",
        "figure.facecolor": C["fondo"],
        "axes.facecolor": C["fondo"],
        "axes.edgecolor": C["gris"],
        "axes.labelcolor": C["navy"],
        "axes.titlecolor": C["navy"],
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlepad": 14,
        "axes.labelsize": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": C["gris_claro"],
        "grid.linewidth": 0.8,
        "xtick.color": C["gris"],
        "ytick.color": C["gris"],
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.frameon": False,
        "legend.fontsize": 10,
        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
        "axes.prop_cycle": mpl.cycler(color=cfg.PALETA_CATEGORICA),
        "axes.formatter.use_locale": False,
    })


def pie_de_figura(fig, texto: str = "Fuente: ENDES 2025 (INEI). Elaboración propia.") -> None:
    """Añade la nota de fuente al pie de una figura."""
    fig.text(0.01, -0.02, texto, fontsize=8, color=C["gris"], ha="left", va="top")


def plantilla_plotly() -> dict:
    """Devuelve el layout base de Plotly con la paleta del proyecto."""
    return {
        "colorway": cfg.PALETA_CATEGORICA,
        "font": {"family": "Segoe UI, sans-serif", "size": 13, "color": C["navy"]},
        "paper_bgcolor": C["fondo"],
        "plot_bgcolor": C["fondo"],
        "title": {"font": {"size": 18, "color": C["navy"]}, "x": 0.02},
        "xaxis": {"gridcolor": C["gris_claro"], "linecolor": C["gris"], "zeroline": False},
        "yaxis": {"gridcolor": C["gris_claro"], "linecolor": C["gris"], "zeroline": False},
        "legend": {"orientation": "h", "y": -0.18},
        "margin": {"l": 70, "r": 30, "t": 70, "b": 70},
    }


def aplicar_plantilla(fig, titulo: str | None = None, mapa: bool = False, **extra):
    """Aplica el tema del proyecto a una figura de Plotly.

    Existe para evitar un error recurrente: la plantilla ya define ``title``
    como diccionario, de modo que pasarlo además como argumento suelto a
    ``update_layout`` lanza «got multiple values for keyword argument». Aquí el
    título se fusiona dentro del diccionario en lugar de competir con él.

    Parameters
    ----------
    fig : plotly.graph_objects.Figure
    titulo : str, optional
        Texto del título.
    mapa : bool, default False
        Si es un mapa, se omiten los ejes cartesianos.
    **extra
        Cualquier otra clave de ``update_layout``.
    """
    layout = plantilla_plotly()
    if mapa:
        layout = {k: v for k, v in layout.items() if k not in ("xaxis", "yaxis")}
    if titulo:
        layout["title"] = {**layout.get("title", {}), "text": titulo}
    layout.update(extra)
    fig.update_layout(**layout)
    return fig


def nueva_figura(*args, **kwargs):
    """Atajo: aplica el tema y devuelve ``plt.subplots``."""
    aplicar_tema()
    return plt.subplots(*args, **kwargs)
