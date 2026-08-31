"""Fase 2 · Cartografía de la salud mental (§7 de la segunda corrida).

Seis mapas sobre los límites oficiales del INEI 2023, cada uno en PNG a 300 dpi,
PDF y HTML interactivo.

**La regla que gobierna todo este módulo:** una estimación territorial con pocos
casos no se pinta. Un mapa da a cada polígono la misma autoridad visual, así que
publicar una provincia estimada con 12 personas junto a Lima con 4 800 engaña
más de lo que informa. Las unidades por debajo del mínimo salen en gris, con su
leyenda propia, y se reporta cuántas quedaron fuera.

Uso
---
    python codigo/scripts/analisis_09_mapas.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from matplotlib.colors import LinearSegmentedColormap

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402
from depresion import (
    geo,  # noqa: E402
    viz,  # noqa: E402
)
from depresion import io as dio  # noqa: E402

COL = cfg.COLORES

#: Escala secuencial perceptualmente uniforme, del claro al navy del proyecto.
#: Se evita el arcoíris a propósito: introduce fronteras visuales donde los
#: datos no las tienen y es ilegible con daltonismo.
ESCALA = LinearSegmentedColormap.from_list("depresion", cfg.PALETA_SECUENCIAL)
# Neutro cálido, no el gris azulado de antes: sobre un fondo de papel un
# gris frío se ve sucio. La trama diagonal es lo que de verdad distingue el
# "sin dato"; el color solo tiene que no competir con la escala.
GRIS_SIN_DATO = "#EDE8DF"

ESCALA_PLOTLY = [[i / (len(cfg.PALETA_SECUENCIAL) - 1), c]
                 for i, c in enumerate(cfg.PALETA_SECUENCIAL)]


def base_analisis() -> pd.DataFrame:
    """Carga la población de análisis con las variables geográficas."""
    df = pd.read_parquet(cfg.DATASET_FINAL)
    return df[df.en_analisis == 1].dropna(subset=["depresion_bin"]).copy()


def _guardar(fig, nombre: str, texto_alt: str) -> None:
    """Guarda una figura de matplotlib en la carpeta de mapas, con texto alternativo."""
    dio.guardar_figura(fig, nombre, cfg.MAPAS)
    (cfg.MAPAS / f"{nombre}_alt.txt").write_text(texto_alt, encoding="utf-8")
    plt.close(fig)


def _pintar(ax, gdf, columna, titulo, etiqueta_leyenda, vmin=None, vmax=None):
    """Dibuja un coroplético marcando sin ambigüedad las unidades sin dato.

    El "sin dato" se dibuja con **trama diagonal**, no con un gris claro. Un
    gris claro se confunde con el extremo bajo de una escala secuencial, y el
    lector acabaría leyendo "sin información" como "prevalencia baja" — que es
    justo el error que la salvaguarda de muestra mínima quiere evitar. La trama
    además sobrevive a la impresión en blanco y negro y al daltonismo.
    """
    con = gdf[gdf[columna].notna()]
    sin = gdf[gdf[columna].isna()]
    if len(sin):
        sin.plot(ax=ax, color=GRIS_SIN_DATO, edgecolor=COL["gris"], linewidth=0.3,
                 hatch="////", zorder=1)
    # Barra horizontal debajo del mapa, no vertical al lado. En vertical el
    # rótulo se escribe girado 90°, y con textos largos como «Ancho del IC 95 %»
    # el contenedor lo recortaba por el borde. Horizontal se lee de corrido y
    # cabe siempre.
    con.plot(ax=ax, column=columna, cmap=ESCALA, edgecolor="white", linewidth=0.35,
             legend=True, vmin=vmin, vmax=vmax, zorder=2,
             legend_kwds={"label": etiqueta_leyenda, "shrink": 0.72,
                          "orientation": "horizontal", "pad": 0.02,
                          "aspect": 34, "fraction": 0.045})
    ax.set_title(titulo, fontsize=13, fontweight="bold", color=COL["navy"], pad=12)
    ax.axis("off")
    if len(sin):
        from matplotlib.patches import Patch
        ax.legend(handles=[Patch(facecolor=GRIS_SIN_DATO, edgecolor=COL["gris"],
                                 hatch="////",
                                 label=f"Muestra insuficiente ({len(sin)})")],
                  loc="lower left", fontsize=8.5, frameon=False)


# ─────────────────────────────────────────────────────────────────────
# Mapa 1 — prevalencia departamental
# ─────────────────────────────────────────────────────────────────────


def mapa_departamental(d: pd.DataFrame) -> pd.DataFrame:
    """Prevalencia de depresión por departamento, con la precisión declarada."""
    from depresion import encuesta as enc

    diseno = enc.crear_diseno(d, ["depresion_bin", "cod_departamento", "departamento"])
    prev = enc.prevalencia(diseno, "depresion_bin", por="cod_departamento", con_deff=False)
    prev = prev.rename(columns={"est": "prevalencia", "lci": "ic_inf", "uci": "ic_sup"})
    conteo = d.cod_departamento.value_counts()
    prev["n"] = prev.cod_departamento.map(conteo)
    prev["amplitud_ic"] = prev.ic_sup - prev.ic_inf
    prev["departamento"] = prev.cod_departamento.map(
        d.drop_duplicates("cod_departamento").set_index("cod_departamento").departamento)

    g = geo.cargar_limites("departamental").merge(
        prev, left_on="cod_departamento", right_on="cod_departamento", how="left")

    viz.aplicar_tema()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 9))
    _pintar(a1, g, "prevalencia", "Prevalencia de depresión (PHQ-9 ≥ 10)",
            "Prevalencia ponderada (%)")
    _pintar(a2, g, "amplitud_ic", "Precisión de la estimación",
            "Amplitud del IC 95 % (puntos porcentuales)")
    fig.suptitle("La depresión se concentra en la sierra sur",
                 fontsize=16, fontweight="bold", color=COL["navy"], y=0.96)
    viz.pie_de_figura(
        fig, "Fuente: ENDES 2025 (INEI); límites INEI 2023 (geogpsperu / SuyoPomalia). "
             "El mapa de la derecha muestra dónde la estimación es menos precisa.")
    _guardar(fig, "mapa_01_departamental",
             "Dos mapas del Perú por departamento. El izquierdo colorea la prevalencia de "
             "depresión: los tonos más oscuros, con los valores más altos, se concentran en "
             "la sierra sur (Puno, Huancavelica, Ayacucho, Apurímac). El derecho muestra la "
             "amplitud del intervalo de confianza: los departamentos amazónicos tienen "
             "estimaciones menos precisas.")

    fig2 = go.Figure(go.Choropleth(
        geojson=json.loads(g.to_json()), locations=g.index, z=g.prevalencia,
        text=g.departamento, colorscale=ESCALA_PLOTLY,
        marker_line_color="white", marker_line_width=0.6,
        colorbar={"title": "Prevalencia (%)"},
        customdata=np.stack([g.n.fillna(0), g.ic_inf, g.ic_sup], axis=-1),
        hovertemplate=("<b>%{text}</b><br>Prevalencia: %{z:.2f} %<br>"
                       "IC 95 %%: %{customdata[1]:.2f} – %{customdata[2]:.2f}<br>"
                       "Personas entrevistadas: %{customdata[0]:,.0f}<extra></extra>")))
    fig2.update_geos(fitbounds="locations", visible=False)
    viz.aplicar_plantilla(fig2, "Prevalencia de depresión por departamento",
                          mapa=True, height=760)
    dio.guardar_figura(fig2, "mapa_01_departamental_interactivo", cfg.MAPAS)
    return prev


# ─────────────────────────────────────────────────────────────────────
# Mapa 2 — provincial, con salvaguarda
# ─────────────────────────────────────────────────────────────────────


def mapa_provincial(d: pd.DataFrame) -> pd.DataFrame:
    """Prevalencia provincial, con las provincias de muestra pequeña en gris."""
    agg = geo.agregar_por_territorio(d, "cod_provincia")
    g = geo.cargar_limites("provincial").merge(agg, on="cod_provincia", how="left")

    viz.aplicar_tema()
    fig, ax = plt.subplots(figsize=(9.5, 11))
    _pintar(ax, g, "prevalencia",
            "Prevalencia provincial de depresión",
            "Prevalencia ponderada (%)")
    estimables = int(agg.estimable.sum())
    sin_muestra = int(g.prevalencia.isna().sum())
    sin_ninguna = sin_muestra - int((~agg.estimable).sum())
    viz.pie_de_figura(
        fig, f"Fuente: ENDES 2025 (INEI); límites INEI 2023. Solo {estimables} de {len(g)} "
             f"provincias alcanzan las {geo.N_MINIMO_TERRITORIAL} personas necesarias para "
             f"estimar. Las {sin_muestra} restantes aparecen tramadas: "
             f"{int((~agg.estimable).sum())} con muestra insuficiente y {sin_ninguna} sin "
             f"ninguna persona entrevistada. Una prevalencia calculada con doce casos no es "
             f"comparable con una calculada con mil.")
    _guardar(fig, "mapa_02_provincial",
             f"Mapa del Perú por provincias. Solo {estimables} de {len(g)} provincias tienen "
             f"muestra suficiente y aparecen coloreadas; las demás están en gris. Entre las "
             f"estimables, los tonos oscuros predominan en la sierra sur.")
    return agg


# ─────────────────────────────────────────────────────────────────────
# Mapa 3 — conglomerados
# ─────────────────────────────────────────────────────────────────────


def mapa_conglomerados(d: pd.DataFrame) -> pd.DataFrame:
    """Puntos de los conglomerados, coloreados por su prevalencia agregada.

    Se agrega **por conglomerado**, nunca por persona: un punto que representara
    un caso individual sería identificable al cruzarlo con otras fuentes.
    """
    g = d.dropna(subset=["longitud", "latitud"]).groupby("conglomerado").agg(
        longitud=("longitud", "first"), latitud=("latitud", "first"),
        n=("depresion_bin", "size"), casos=("depresion_bin", "sum"),
        altitud=("altitud", "first")).reset_index()
    g["prevalencia"] = g.casos / g.n * 100
    g = g[g.n >= 5]   # un conglomerado con menos de 5 personas no se dibuja

    limites = geo.cargar_limites("departamental")

    viz.aplicar_tema()
    fig, ax = plt.subplots(figsize=(9.5, 11))
    limites.plot(ax=ax, color="#F2F5F9", edgecolor="white", linewidth=0.5, zorder=1)
    sc = ax.scatter(g.longitud, g.latitud, c=g.prevalencia, cmap=ESCALA,
                    s=np.sqrt(g.n) * 3.6, alpha=0.72, edgecolor="none", zorder=3,
                    vmin=0, vmax=np.percentile(g.prevalencia, 97))
    cb = fig.colorbar(sc, ax=ax, shrink=0.72, pad=0.02,
                      orientation="horizontal", aspect=34, fraction=0.045)
    cb.set_label("Prevalencia del conglomerado (%)")
    ax.set_title(f"Los {len(g):,} conglomerados de la muestra",
                 fontsize=13, fontweight="bold", color=COL["navy"], pad=12)
    ax.axis("off")
    viz.pie_de_figura(
        fig, "Fuente: ENDES 2025 (INEI). Cada punto es un conglomerado muestral, no una "
             "persona: el color es la prevalencia agregada del grupo y el tamaño, el número "
             "de entrevistados. No se representa ningún caso individual.")
    _guardar(fig, "mapa_03_conglomerados",
             f"Mapa de puntos del Perú con {len(g):,} conglomerados muestrales. Los puntos "
             f"se distribuyen por todo el territorio, más densos en la costa y la sierra. "
             f"El color indica la prevalencia agregada del conglomerado.")
    return g


# ─────────────────────────────────────────────────────────────────────
# Mapa 4 — altitud y prevalencia
# ─────────────────────────────────────────────────────────────────────


def mapa_bivariado(d: pd.DataFrame, prev_dep: pd.DataFrame) -> None:
    """Altitud media y prevalencia lado a lado, para ver si el patrón se superpone."""
    alt = d.groupby("cod_departamento").altitud.mean().rename("altitud_media").reset_index()
    g = (geo.cargar_limites("departamental")
         .merge(prev_dep[["cod_departamento", "prevalencia", "departamento"]],
                on="cod_departamento", how="left")
         .merge(alt, on="cod_departamento", how="left"))

    viz.aplicar_tema()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 9))
    _pintar(a1, g, "altitud_media", "Altitud media del departamento", "Metros sobre el mar")
    _pintar(a2, g, "prevalencia", "Prevalencia de depresión", "Prevalencia ponderada (%)")
    r = np.corrcoef(g.altitud_media.dropna(), g.prevalencia.dropna())[0, 1]
    fig.suptitle(f"Los dos mapas se parecen: la correlación entre ambos es {r:.2f}",
                 fontsize=15, fontweight="bold", color=COL["navy"], y=0.955)
    viz.pie_de_figura(
        fig, "Fuente: ENDES 2025 (INEI). La coincidencia entre ambos mapas es una "
             "correlación ecológica entre agregados departamentales; no permite concluir "
             "que la altura cause depresión.")
    _guardar(fig, "mapa_04_altitud_prevalencia",
             f"Dos mapas del Perú lado a lado. El izquierdo muestra la altitud media por "
             f"departamento, con la sierra en tonos oscuros. El derecho muestra la "
             f"prevalencia de depresión. Los patrones se parecen: la correlación es {r:.2f}.")


# ─────────────────────────────────────────────────────────────────────
# Mapa 5 — brecha de atención
# ─────────────────────────────────────────────────────────────────────


def mapa_brecha(d: pd.DataFrame) -> pd.DataFrame:
    """Dónde es peor la brecha de atención entre quienes dan positivo al tamizaje."""
    con = d[d.depresion_bin == 1]
    agg = con.groupby("cod_departamento").agg(
        n=("brecha_atencion", "size"), brecha=("brecha_atencion", "mean")).reset_index()
    agg["brecha"] = agg.brecha * 100
    agg["estimable"] = agg.n >= 30
    agg.loc[~agg.estimable, "brecha"] = np.nan

    g = geo.cargar_limites("departamental").merge(agg, on="cod_departamento", how="left")
    nacional = con.brecha_atencion.mean() * 100

    viz.aplicar_tema()
    fig, ax = plt.subplots(figsize=(9.5, 11))
    _pintar(ax, g, "brecha", "Personas con depresión que no recibieron atención",
            "Brecha de atención (%)")
    ax.set_title(f"Casi nadie recibe atención, y en algunos departamentos, nadie\n"
                 f"Media nacional: {nacional:.1f} %",
                 fontsize=13, fontweight="bold", color=COL["navy"], pad=12)
    viz.pie_de_figura(
        fig, "Fuente: ENDES 2025 (INEI). Se calcula solo entre quienes dan positivo al "
             "tamizaje. Los departamentos con menos de 30 casos positivos no se estiman.")
    _guardar(fig, "mapa_05_brecha_atencion",
             f"Mapa del Perú por departamento con la brecha de atención en salud mental. "
             f"Casi todo el país aparece en tonos oscuros, por encima del 80 %. La media "
             f"nacional es {nacional:.1f} %.")
    return agg


# ─────────────────────────────────────────────────────────────────────
# Mapa 6 — densidad ponderada
# ─────────────────────────────────────────────────────────────────────


def mapa_densidad(d: pd.DataFrame) -> None:
    """Dónde se concentran los casos en términos absolutos, no de tasa.

    Un mapa de prevalencia responde "¿dónde es más probable?"; este responde
    "¿dónde están?". Son preguntas distintas y llevan a políticas distintas: la
    tasa señala dónde investigar, el volumen señala dónde atender.
    """
    casos = d[(d.depresion_bin == 1) & d.longitud.notna()]
    limites = geo.cargar_limites("departamental")

    viz.aplicar_tema()
    fig, ax = plt.subplots(figsize=(9.5, 11))
    limites.plot(ax=ax, color="#F7F9FC", edgecolor=COL["gris_claro"], linewidth=0.5, zorder=1)
    hb = ax.hexbin(casos.longitud, casos.latitud, C=casos.peso, reduce_C_function=np.sum,
                   gridsize=42, cmap=ESCALA, mincnt=1, zorder=2, linewidths=0)
    cb = fig.colorbar(hb, ax=ax, shrink=0.72, pad=0.02,
                      orientation="horizontal", aspect=34, fraction=0.045)
    cb.set_label("Casos ponderados en la celda")
    ax.set_title("Dónde se concentran los casos, no dónde la tasa es más alta",
                 fontsize=13, fontweight="bold", color=COL["navy"], pad=12)
    ax.axis("off")
    viz.pie_de_figura(
        fig, "Fuente: ENDES 2025 (INEI). Suma de pesos muestrales de quienes dan positivo, "
             "por celda hexagonal. Lima concentra el volumen aunque su tasa no sea la más "
             "alta: es el mapa que importa para dimensionar servicios.")
    _guardar(fig, "mapa_06_densidad_casos",
             "Mapa de densidad hexagonal del Perú. Las celdas más oscuras, con más casos "
             "ponderados, se concentran en la costa central alrededor de Lima y en los "
             "principales núcleos urbanos.")


def main() -> None:
    """Genera los seis mapas y sus tablas de respaldo."""
    dio.configurar_logging()
    cfg.MAPAS.mkdir(parents=True, exist_ok=True)
    d = base_analisis()
    print(f"Población de análisis: {len(d):,}\n")

    prev_dep = mapa_departamental(d)
    dio.guardar_tabla(prev_dep, "tabla_48_prevalencia_departamental_geo",
                      "Prevalencia departamental con amplitud del intervalo")
    print("Mapa 1 · departamental — listo")
    print(prev_dep.nlargest(5, "prevalencia")[
        ["departamento", "n", "prevalencia", "ic_inf", "ic_sup"]].to_string(index=False))

    prov = mapa_provincial(d)
    dio.guardar_tabla(prov, "tabla_49_prevalencia_provincial",
                      "Prevalencia provincial con la marca de estimabilidad")
    print(f"\nMapa 2 · provincial — {int(prov.estimable.sum())} de {len(prov)} provincias "
          f"estimables (n ≥ {geo.N_MINIMO_TERRITORIAL})")
    print(f"  Provincias descartadas por muestra insuficiente: {int((~prov.estimable).sum())}")
    print(f"  Mediana de n en las descartadas: {prov[~prov.estimable].n.median():.0f} personas")

    cong = mapa_conglomerados(d)
    print(f"\nMapa 3 · conglomerados — {len(cong):,} puntos dibujados")

    mapa_bivariado(d, prev_dep)
    print("Mapa 4 · altitud y prevalencia — listo")

    brecha = mapa_brecha(d)
    dio.guardar_tabla(brecha, "tabla_50_brecha_departamental",
                      "Brecha de atención por departamento")
    print(f"\nMapa 5 · brecha de atención — {int(brecha.estimable.sum())} departamentos "
          f"estimables")
    peores = brecha[brecha.estimable].nlargest(5, "brecha")
    print(peores[["cod_departamento", "n", "brecha"]].to_string(index=False))

    mapa_densidad(d)
    print("\nMapa 6 · densidad de casos — listo")

    # GeoJSON ligero para el boletín y la web
    cfg.GEOJSON_WEB.mkdir(parents=True, exist_ok=True)
    g = geo.cargar_limites("departamental").merge(
        prev_dep[["cod_departamento", "prevalencia", "ic_inf", "ic_sup", "n", "departamento"]],
        on="cod_departamento", how="left")
    info = geo.exportar_geojson(g, cfg.GEOJSON_WEB / "departamentos.geojson", tolerancia=0.012)
    print(f"\nGeoJSON para la web: {info}")
    print("\nCartografía completada.")


if __name__ == "__main__":
    main()
