"""Fase 2 · Descriptivo y medidas de frecuencia (§11.1 del protocolo).

Produce la Tabla 1 de artículo, las prevalencias ponderadas con intervalo de
confianza bajo diseño complejo, el perfil de los nueve ítems del PHQ-9, el
mapa coroplético por departamento y la brecha de atención.

Uso
---
    python codigo/scripts/analisis_02_descriptivo.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402
from depresion import encuesta as enc  # noqa: E402
from depresion import io as dio  # noqa: E402
from depresion import viz  # noqa: E402

C = cfg.COLORES

ETIQUETAS = {
    "sexo": "Sexo", "grupo_etario": "Grupo etario", "educacion_grupo": "Nivel educativo",
    "area": "Área de residencia", "region_natural": "Región natural",
    "dominio_inei": "Dominio", "departamento": "Departamento",
}


# ─────────────────────────────────────────────────────────────────────
# Tabla 1
# ─────────────────────────────────────────────────────────────────────


def v_de_cramer(t: pd.DataFrame) -> float:
    """V de Cramér como tamaño de efecto para una tabla de contingencia."""
    chi2 = stats.chi2_contingency(t)[0]
    n = t.values.sum()
    return np.sqrt(chi2 / (n * (min(t.shape) - 1)))


def tabla_uno(df: pd.DataFrame) -> pd.DataFrame:
    """Construye la Tabla 1: características de la muestra por desenlace.

    Para categóricas usa chi-cuadrado y V de Cramér; para continuas, la t de
    Welch (que no asume varianzas iguales) y la d de Cohen.
    """
    filas = []
    categoricas = ["sexo", "grupo_etario", "educacion_grupo", "area", "region_natural",
                   "estado_pareja", "alcohol_categoria", "tabaco_categoria", "imc_categoria"]
    continuas = ["edad", "imc", "presion_sistolica"]

    n_tot, n_sin, n_con = len(df), int((df.depresion_bin == 0).sum()), int((df.depresion_bin == 1).sum())
    filas.append({"variable": "N", "categoria": "", "total": f"{n_tot:,}",
                  "sin_depresion": f"{n_sin:,}", "con_depresion": f"{n_con:,}",
                  "p": "", "tamano_efecto": "", "prueba": ""})

    for v in categoricas:
        if v not in df.columns:
            continue
        d = df[[v, "depresion_bin"]].dropna()
        t = pd.crosstab(d[v].astype(str), d.depresion_bin)
        if t.shape[0] < 2:
            continue
        p = stats.chi2_contingency(t)[1]
        efecto = v_de_cramer(t)
        primera = True
        for cat in t.index:
            tot = int(t.loc[cat].sum())
            sin_, con = int(t.loc[cat, 0.0]), int(t.loc[cat, 1.0])
            filas.append({
                "variable": ETIQUETAS.get(v, v) if primera else "",
                "categoria": cat,
                "total": f"{tot:,} ({tot / len(d) * 100:.1f})",
                "sin_depresion": f"{sin_:,} ({sin_ / t[0.0].sum() * 100:.1f})",
                "con_depresion": f"{con:,} ({con / t[1.0].sum() * 100:.1f})",
                "p": f"{p:.2e}" if primera and p < 0.001 else (f"{p:.3f}" if primera else ""),
                "tamano_efecto": f"V = {efecto:.3f}" if primera else "",
                "prueba": "χ² de Pearson" if primera else "",
            })
            primera = False

    for v in continuas:
        if v not in df.columns:
            continue
        a = df.loc[df.depresion_bin == 0, v].dropna()
        b = df.loc[df.depresion_bin == 1, v].dropna()
        if len(a) < 2 or len(b) < 2:
            continue
        t_stat, p = stats.ttest_ind(a, b, equal_var=False)
        s_pool = np.sqrt(((len(a) - 1) * a.var() + (len(b) - 1) * b.var()) / (len(a) + len(b) - 2))
        d_cohen = (b.mean() - a.mean()) / s_pool
        todo = df[v].dropna()
        filas.append({
            "variable": v.replace("_", " ").capitalize(), "categoria": "media (DE)",
            "total": f"{todo.mean():.1f} ({todo.std():.1f})",
            "sin_depresion": f"{a.mean():.1f} ({a.std():.1f})",
            "con_depresion": f"{b.mean():.1f} ({b.std():.1f})",
            "p": f"{p:.2e}" if p < 0.001 else f"{p:.3f}",
            "tamano_efecto": f"d = {d_cohen:.3f}", "prueba": "t de Welch",
        })
    return pd.DataFrame(filas)


# ─────────────────────────────────────────────────────────────────────
# Ítems del PHQ-9
# ─────────────────────────────────────────────────────────────────────


def perfil_items(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula, para cada ítem, la prevalencia de respuesta positiva y su peso.

    Excluye del ranking el ítem sensible de autolesión, que se reporta pero no
    se destaca (§15.3).
    """
    filas = []
    for v in cfg.ITEMS_PHQ9:
        s = df[v].dropna()
        filas.append({
            "item": v,
            "sintoma": cfg.ETIQUETAS_PHQ9[v],
            "n": len(s),
            "media": s.mean(),
            "pct_ningun_dia": (s == 0).mean() * 100,
            "pct_varios_dias": (s == 1).mean() * 100,
            "pct_mayoria_dias": (s == 2).mean() * 100,
            "pct_casi_todos": (s == 3).mean() * 100,
            "pct_positivo": (s >= 1).mean() * 100,
            "pct_relevante": (s >= 2).mean() * 100,
            "sensible": v == cfg.ITEM_SENSIBLE,
        })
    out = pd.DataFrame(filas).sort_values("media", ascending=False)
    # Consistencia interna
    alfa = alfa_cronbach(df[cfg.ITEMS_PHQ9].dropna())
    out.attrs["alfa_cronbach"] = alfa
    return out


def alfa_cronbach(x: pd.DataFrame) -> float:
    """Calcula el alfa de Cronbach de un conjunto de ítems."""
    k = x.shape[1]
    var_items = x.var(axis=0, ddof=1).sum()
    var_total = x.sum(axis=1).var(ddof=1)
    return (k / (k - 1)) * (1 - var_items / var_total)


# ─────────────────────────────────────────────────────────────────────
# Figuras
# ─────────────────────────────────────────────────────────────────────


def figura_distribucion(df: pd.DataFrame) -> None:
    """Histograma del PHQ-9 con los puntos de corte marcados."""
    import matplotlib.pyplot as plt

    viz.aplicar_tema()
    fig, ax = plt.subplots(figsize=(10, 5.5))
    s = df.phq9_score.dropna()
    ax.hist(s, bins=np.arange(-0.5, 28.5, 1), color=C["navy"], edgecolor="white", linewidth=0.6)
    for corte, etq, col in [(5, "Leve", C["ambar"]), (10, "Moderada", C["rojo"]),
                            (15, "Mod. severa", C["rojo"]), (20, "Severa", C["rojo"])]:
        ax.axvline(corte - 0.5, color=col, linestyle="--", linewidth=1.4, alpha=0.85)
        ax.text(corte - 0.3, ax.get_ylim()[1] * 0.93, etq, fontsize=8.5, color=col, rotation=90, va="top")
    ax.set_xlabel("Puntaje PHQ-9")
    ax.set_ylabel("Número de personas")
    ax.set_title("Distribución del puntaje PHQ-9")
    ax.text(0.97, 0.93,
            f"n = {len(s):,}\nmedia = {s.mean():.2f}\nasimetría = {stats.skew(s):.2f}\n"
            f"{(s == 0).mean() * 100:.1f} % en cero",
            transform=ax.transAxes, ha="right", va="top", fontsize=9.5, color=C["gris"],
            bbox={"boxstyle": "round,pad=0.6", "facecolor": "#F7F9FC", "edgecolor": C["gris_claro"]})
    viz.pie_de_figura(fig)
    dio.guardar_figura(fig, "fig_01_distribucion_phq9")
    plt.close(fig)


def figura_prevalencias(tabla: pd.DataFrame) -> None:
    """Gráfico de barras horizontales con las prevalencias e IC por subgrupo."""
    import matplotlib.pyplot as plt

    viz.aplicar_tema()
    d = tabla[tabla.variable != "Departamento"].copy()
    d = d[d.variable != "Total"]
    fig, ax = plt.subplots(figsize=(9.5, max(6, 0.36 * len(d))))
    y = np.arange(len(d))[::-1]
    colores = {v: c for v, c in zip(d.variable.unique(), cfg.PALETA_CATEGORICA, strict=False)}
    ax.barh(y, d.prevalencia, color=[colores[v] for v in d.variable], height=0.68, alpha=0.9)
    ax.errorbar(d.prevalencia, y, xerr=[d.prevalencia - d.ic_inf, d.ic_sup - d.prevalencia],
                fmt="none", ecolor=C["navy"], elinewidth=1.3, capsize=3)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r.categoria}" for _, r in d.iterrows()], fontsize=9.5)
    for yi, (_, r) in zip(y, d.iterrows(), strict=False):
        ax.text(r.ic_sup + 0.18, yi, f"{r.prevalencia:.1f}", va="center", fontsize=8.8, color=C["gris"])
    ax.set_xlabel("Prevalencia ponderada de depresión (%)  ·  IC 95 %")
    ax.set_title("Prevalencia de depresión (PHQ-9 ≥ 10) por subgrupo")
    ax.set_xlim(0, max(d.ic_sup) * 1.15)
    viz.pie_de_figura(fig)
    dio.guardar_figura(fig, "fig_02_prevalencia_subgrupos")
    plt.close(fig)


def figura_items(perfil: pd.DataFrame) -> None:
    """Barras apiladas de la distribución de respuesta de cada ítem."""
    import matplotlib.pyplot as plt

    viz.aplicar_tema()
    d = perfil.sort_values("media")
    fig, ax = plt.subplots(figsize=(11, 6))
    izq = np.zeros(len(d))
    cols = ["pct_ningun_dia", "pct_varios_dias", "pct_mayoria_dias", "pct_casi_todos"]
    paleta = [C["gris_claro"], C["dorado_claro"], C["ambar"], C["rojo"]]
    for c, col, etq in zip(cols, paleta, cfg.ESCALA_PHQ9.values(), strict=False):
        ax.barh(np.arange(len(d)), d[c], left=izq, color=col, label=etq, height=0.72)
        izq += d[c].values
    ax.set_yticks(np.arange(len(d)))
    ax.set_yticklabels([f"{r.sintoma}{' (*)' if r.sensible else ''}" for _, r in d.iterrows()], fontsize=9.5)
    ax.set_xlabel("Porcentaje de la población (%)")
    ax.set_title("Frecuencia de cada síntoma del PHQ-9 en los últimos 14 días")
    ax.legend(ncol=4, loc="lower center", bbox_to_anchor=(0.5, -0.18), fontsize=9)
    ax.set_xlim(0, 100)
    viz.pie_de_figura(fig, "Fuente: ENDES 2025 (INEI). ⚠ Ítem sensible: se reporta pero no se analiza por separado.")
    dio.guardar_figura(fig, "fig_03_items_phq9")
    plt.close(fig)


def figura_mapa(prev_dep: pd.DataFrame) -> dict:
    """Mapa coroplético de prevalencia por departamento.

    Verifica que los 25 departamentos crucen con el GeoJSON y reporta
    cualquiera que no lo haga, en lugar de dejarlo en blanco.
    """
    ruta = cfg.DATOS_EXTERNOS / "peru_departamentos.geojson"
    geo = json.loads(ruta.read_text(encoding="utf-8"))
    nombres_geo = {cfg.normalizar_texto(f["properties"]["NOMBDEP"]) for f in geo["features"]}
    for f in geo["features"]:
        f["id"] = cfg.normalizar_texto(f["properties"]["NOMBDEP"])

    nombres_datos = set(prev_dep.departamento_norm)
    sin_cruce_datos = sorted(nombres_datos - nombres_geo)
    sin_cruce_geo = sorted(nombres_geo - nombres_datos)
    informe = {"n_geojson": len(nombres_geo), "n_datos": len(nombres_datos),
               "sin_cruce_en_datos": sin_cruce_datos, "sin_cruce_en_geojson": sin_cruce_geo,
               "match_completo": not sin_cruce_datos and not sin_cruce_geo}

    fig = px.choropleth(
        prev_dep, geojson=geo, locations="departamento_norm",
        color="prevalencia", hover_name="departamento",
        hover_data={"departamento_norm": False, "prevalencia": ":.2f",
                    "ic_inf": ":.2f", "ic_sup": ":.2f", "n": True},
        color_continuous_scale=cfg.PALETA_SECUENCIAL,
        labels={"prevalencia": "Prevalencia (%)"},
    )
    fig.update_geos(fitbounds="locations", visible=False)
    layout = {k: v for k, v in viz.plantilla_plotly().items() if k not in ("xaxis", "yaxis")}
    layout["title"] = {**layout.get("title", {}),
                       "text": "Prevalencia de depresión (PHQ-9 ≥ 10) por departamento"}
    fig.update_layout(**layout, height=760)
    dio.guardar_figura(fig, "fig_04_mapa_departamentos", cfg.MAPAS)
    return informe


def figura_brecha(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula y grafica la brecha de atención por subgrupo."""
    import matplotlib.pyplot as plt

    con = df[df.depresion_bin == 1]
    filas = [{"grupo": "Nacional", "categoria": "Total", "n": len(con),
              "brecha": con.brecha_atencion.mean() * 100}]
    for v in ["sexo", "area", "region_natural", "educacion_grupo", "grupo_etario"]:
        for cat, g in con.groupby(v, observed=True):
            if len(g) < 30:
                continue
            filas.append({"grupo": ETIQUETAS.get(v, v), "categoria": str(cat),
                          "n": len(g), "brecha": g.brecha_atencion.mean() * 100})
    out = pd.DataFrame(filas)

    viz.aplicar_tema()
    d = out[out.grupo != "Nacional"]
    fig, ax = plt.subplots(figsize=(9.5, max(5.5, 0.38 * len(d))))
    y = np.arange(len(d))[::-1]
    colores = {v: c for v, c in zip(d.grupo.unique(), cfg.PALETA_CATEGORICA, strict=False)}
    ax.barh(y, d.brecha, color=[colores[v] for v in d.grupo], height=0.68, alpha=0.9)
    nacional = out.brecha.iloc[0]
    ax.axvline(nacional, color=C["rojo"], linestyle="--", linewidth=1.6)
    ax.text(nacional - 1, len(d) * 0.02, f"Nacional {nacional:.1f} %", color=C["rojo"],
            fontsize=9.5, rotation=90, va="bottom", ha="right")
    ax.set_yticks(y)
    ax.set_yticklabels(d.categoria, fontsize=9.5)
    for yi, (_, r) in zip(y, d.iterrows(), strict=False):
        ax.text(r.brecha + 0.6, yi, f"{r.brecha:.1f}", va="center", fontsize=8.8, color=C["gris"])
    ax.set_xlabel("Personas con depresión que NO recibieron atención (%)")
    ax.set_title("Brecha de atención en salud mental")
    ax.set_xlim(0, 100)
    viz.pie_de_figura(fig)
    dio.guardar_figura(fig, "fig_05_brecha_atencion")
    plt.close(fig)
    return out


# ─────────────────────────────────────────────────────────────────────
# Orquestador
# ─────────────────────────────────────────────────────────────────────


def main() -> None:
    """Ejecuta el análisis descriptivo completo."""
    dio.configurar_logging()
    df = pd.read_parquet(cfg.DATASET_FINAL)
    base = df[df.en_analisis == 1].dropna(subset=["depresion_bin"]).copy()
    print(f"Población de análisis: {len(base):,}\n")

    # Ficha del diseño
    ficha = enc.resumen_diseno(base)
    dio.guardar_tabla(ficha, "tabla_06_ficha_diseno_muestral", "Ficha del diseño muestral complejo")
    print(ficha.to_string(index=False))

    # Tabla 1
    t1 = tabla_uno(base)
    dio.guardar_tabla(t1, "tabla_07_caracteristicas_muestra",
                      "Características de la muestra según presencia de depresión")

    # Prevalencias ponderadas
    variables = ["sexo", "grupo_etario", "educacion_grupo", "area", "region_natural", "dominio_inei"]
    prev = enc.tabla_prevalencias(base, variables, etiquetas=ETIQUETAS)
    dio.guardar_tabla(prev, "tabla_08_prevalencias_ponderadas",
                      "Prevalencia ponderada de depresión con IC 95 % bajo diseño complejo")
    print("\n" + "=" * 88)
    print("PREVALENCIAS PONDERADAS (IC 95 %, diseño complejo)")
    print("=" * 88)
    print(prev[["variable", "categoria", "n", "prevalencia", "ic_95", "deff"]].to_string(index=False))

    # Por departamento
    dis_dep = enc.crear_diseno(base, ["depresion_bin", "departamento", "departamento_norm"])
    pd_dep = enc.prevalencia(dis_dep, "depresion_bin", por="departamento", con_deff=False)
    pd_dep = pd_dep.rename(columns={"est": "prevalencia", "lci": "ic_inf", "uci": "ic_sup"})
    conteo = base.departamento.value_counts()
    pd_dep["n"] = pd_dep.departamento.map(conteo)
    pd_dep["departamento_norm"] = pd_dep.departamento.map(cfg.normalizar_texto)
    pd_dep = pd_dep.sort_values("prevalencia", ascending=False)
    dio.guardar_tabla(pd_dep, "tabla_09_prevalencia_departamento",
                      "Prevalencia ponderada de depresión por departamento")
    print("\nDepartamentos con mayor y menor prevalencia:")
    print(pd_dep[["departamento", "n", "prevalencia", "ic_inf", "ic_sup"]].head(5).to_string(index=False))
    print(pd_dep[["departamento", "n", "prevalencia", "ic_inf", "ic_sup"]].tail(3).to_string(index=False))

    # Ítems
    perfil = perfil_items(base)
    dio.guardar_tabla(perfil, "tabla_10_items_phq9", "Perfil de respuesta de los nueve ítems del PHQ-9")
    print(f"\nAlfa de Cronbach de los 9 ítems: {perfil.attrs['alfa_cronbach']:.3f}")

    # Brecha de atención
    brecha = figura_brecha(base)
    dio.guardar_tabla(brecha, "tabla_11_brecha_atencion", "Brecha de atención en salud mental por subgrupo")
    print(f"\nBrecha de atención nacional: {brecha.brecha.iloc[0]:.1f} %")

    # Figuras
    figura_distribucion(base)
    figura_prevalencias(prev)
    figura_items(perfil)
    informe_mapa = figura_mapa(pd_dep)
    print(f"\nCruce con el GeoJSON: {informe_mapa}")
    if not informe_mapa["match_completo"]:
        print("  ⚠️ ATENCIÓN: hay departamentos sin cruzar. Revisar la normalización.")

    (cfg.LOGS / "informe_mapa.json").write_text(
        json.dumps(informe_mapa, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nDescriptivo completado.")


if __name__ == "__main__":
    main()
