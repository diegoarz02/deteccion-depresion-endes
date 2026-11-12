"""Dibuja el flujograma STROBE de conformación de la muestra.

Se dibuja con matplotlib en vez de graphviz para no depender del binario
``dot``, que no está instalado en el equipo y complicaría la reproducción.

Uso
---
    python codigo/scripts/figura_strobe.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402
from depresion import viz  # noqa: E402

C = cfg.COLORES


def caja(ax, x, y, ancho, alto, titulo, detalle, color_borde, relleno,
         fs_titulo=11, fs_detalle=9):
    """Dibuja una caja redondeada con título en negrita y detalle debajo.

    El título se centra en el tercio superior y el detalle en el inferior, de
    modo que ambos quepan aunque tengan varias líneas.
    """
    ax.add_patch(FancyBboxPatch(
        (x, y), ancho, alto,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        linewidth=1.6, edgecolor=color_borde, facecolor=relleno, zorder=2,
    ))
    n_tit = titulo.count("\n") + 1
    n_det = detalle.count("\n") + 1
    # Reparte el alto disponible en proporción al número de líneas de cada bloque.
    frac = n_tit / (n_tit + n_det)
    ax.text(x + ancho / 2, y + alto * (1 - frac / 2), titulo, ha="center", va="center",
            fontsize=fs_titulo, fontweight="bold", color=C["navy"], zorder=3,
            linespacing=1.35)
    ax.text(x + ancho / 2, y + alto * (1 - frac) / 2, detalle, ha="center", va="center",
            fontsize=fs_detalle, color=C["gris"], zorder=3, linespacing=1.45)


def flecha(ax, x, y0, y1, color=None):
    """Dibuja una flecha vertical descendente."""
    ax.add_patch(FancyArrowPatch(
        (x, y0), (x, y1), arrowstyle="-|>", mutation_scale=16,
        linewidth=1.4, color=color or C["navy"], zorder=1,
    ))


def main() -> None:
    """Genera ``docs/flujograma_strobe.png`` y su versión PDF."""
    viz.aplicar_tema()
    flujo = pd.read_csv(cfg.TABLAS / "tabla_04_flujograma_strobe.csv")

    fig, ax = plt.subplots(figsize=(11.5, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 11.4)
    ax.axis("off")

    etapas = [
        ("Personas de 15 años a más\nENDES 2025 — módulo CSALUD01",
         f"N = {flujo.n[0]:,}".replace(",", " ")),
        ("Con PHQ-9 completo",
         f"N = {flujo.n[1]:,}".replace(",", " ")),
        ("Con ponderador asignado",
         f"N = {flujo.n[2]:,}".replace(",", " ")),
        ("Población de análisis\ncovariables clave completas",
         f"N = {flujo.n[3]:,}".replace(",", " ")),
    ]
    exclusiones = [
        (f"Excluidos: {flujo.excluidos[1]:,}".replace(",", " "),
         "PHQ-9 incompleto (QSRESULT)\n"
         "ausente 777 · rechazada 899\nincompleta 1 419\ndiscapacidad 70 · otra 3"),
        (f"Excluidos: {flujo.excluidos[2]:,}".replace(",", " "),
         "Sin Peso15_AMAS\nno pueden entrar al análisis\ncon diseño complejo"),
        (f"Excluidos: {flujo.excluidos[3]:,}".replace(",", " "),
         "Nunca asistieron a la escuela\n(sin nivel educativo, QS24 = 2)\n3,79 % de la base"),
    ]

    x_c, ancho, alto = 0.9, 4.9, 1.4
    x_e, ancho_e, alto_e = 6.35, 3.35, 1.35
    ys = [8.3, 5.85, 3.4, 0.95]

    for i, (titulo, detalle) in enumerate(etapas):
        final = i == len(etapas) - 1
        caja(ax, x_c, ys[i], ancho, alto, titulo, detalle,
             C["dorado"] if final else C["navy"],
             "#FDF8E7" if final else "#F7F9FC")

    for i, (titulo, detalle) in enumerate(exclusiones):
        y = ys[i] - 1.4
        caja(ax, x_e, y, ancho_e, alto_e, titulo, detalle, C["rojo"], "#FDF3F3",
             fs_titulo=10.5, fs_detalle=8.5)
        flecha(ax, x_c + ancho / 2, ys[i], ys[i + 1] + alto)
        ax.add_patch(FancyArrowPatch(
            (x_c + ancho / 2, ys[i] - 0.5), (x_e, y + alto_e / 2),
            arrowstyle="-|>", mutation_scale=13, linewidth=1.1,
            color=C["rojo"], linestyle=(0, (4, 2)), zorder=1,
        ))

    ax.text(0.15, 11.3, "Flujograma STROBE", fontsize=17, fontweight="bold",
            color=C["navy"], va="top")
    ax.text(0.15, 10.85,
            "Conformación de la muestra analítica · Depresión en población de 15 y más años",
            fontsize=10.5, color=C["gris"], va="top")
    ax.text(0.15, 0.4,
            "Fuente: ENDES 2025 (INEI), módulos CSALUD01 y RECH0. Elaboración propia.",
            fontsize=8.5, color=C["gris"], va="top")

    for ext in ("png", "pdf"):
        destino = cfg.DOCS / f"flujograma_strobe.{ext}"
        fig.savefig(destino, dpi=cfg.DPI_FIGURAS, bbox_inches="tight",
                    facecolor=C["fondo"])
        print(f"escrito: {destino}")
    plt.close(fig)


if __name__ == "__main__":
    main()
