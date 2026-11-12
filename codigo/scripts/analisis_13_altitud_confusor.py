"""Fase 2 · La altitud como posible confusor, y su propia asociación bajo ajuste.

La altitud no viaja sola: va con la región, la ruralidad, la pobreza y el acceso
a servicios. Por eso cumple dos papeles a la vez, y este script mira los dos.

1. **Altitud como confusor de los demás factores.** Para cada exposición
   principal se compara el OR (y la razón de prevalencias) sin y con ajuste por
   altitud, con el criterio convencional del cambio del 10 % en el estimador
   (Mickey y Greenland, 1989). Si cambia 10 % o más, la altitud confunde esa
   asociación y corresponde reportar la ajustada.

2. **Asociación de la altitud con la depresión**, cruda y luego ajustada por
   bloques: sociodemográficas, conductas y condiciones clínicas, región natural
   y, como control más fino, departamento. Con el departamento en el modelo, el
   gradiente se identifica solo con la variación de altitud *dentro* de cada
   departamento, que es lo más cercano a separar la altitud del resto de lo que
   distingue a un departamento de otro.

3. **Lo ecológico frente a lo individual.** El gradiente de los mapas por
   departamento es una correlación entre agregados; aquí se pone al lado de la
   estimación individual con departamento fijo para ver cuánto se atenúa.

No es un modelo nuevo: usa el mismo diseño muestral y las mismas covariables que
el modelo logístico principal. La región natural se deriva de la altitud del
conglomerado, de modo que adjuntarla junto a la altitud es controlar por una
versión gruesa de la propia exposición. Se reporta con esa advertencia, no se
omite.

Uso
---
    python codigo/scripts/analisis_13_altitud_confusor.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import NullFormatter, NullLocator
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402
from depresion import (
    geo,  # noqa: E402
    viz,  # noqa: E402
)
from depresion import io as dio  # noqa: E402
from depresion import modelos as mod  # noqa: E402
from depresion import sensibilidad as sens  # noqa: E402

warnings.filterwarnings("ignore")
COL = cfg.COLORES

UMBRAL_CONFUSION = 10.0  # % de cambio en el estimador

SOCIODEMOGRAFICAS = ["es_mujer", "grupo_etario", "educacion_grupo", "es_rural", "region_natural"]
CONDUCTUALES_CLINICAS = ["consumo_frecuente", "alcohol_problematico", "fuma_12m",
                         "hta_dx", "diabetes_dx", "obesidad"]
COMPLETO = SOCIODEMOGRAFICAS + CONDUCTUALES_CLINICAS

# Covariables del modelo de altitud de analisis_07_altitud.py (tabla 38): se
# conservan idénticas para que el escalonado de aquí reproduzca esa tabla.
AJUSTE_ALTITUD = ["es_mujer", "grupo_etario", "educacion_grupo", "es_rural",
                  "hta_dx", "diabetes_dx", "fuma_12m", "consumo_frecuente"]

REFERENCIAS = {
    "grupo_etario": "30-39", "educacion_grupo": "Superior", "region_natural": "Costa",
    "altitud_categoria": geo.ORDEN_PISOS[0], "departamento": "Lima",
    "educacion_4": "Superior",
}

EXPOSICIONES = [
    ("es_mujer", "Sexo femenino"),
    ("es_rural", "Área rural"),
    ("alcohol_problematico", "Consumo problemático de alcohol"),
    ("consumo_frecuente", "Consumo frecuente de alcohol"),
    ("fuma_12m", "Fumó en los últimos 12 meses"),
    ("hta_dx", "Hipertensión diagnosticada"),
    ("diabetes_dx", "Diabetes diagnosticada"),
    ("obesidad", "Obesidad (IMC ≥ 30)"),
    ("violencia_fisica", "Violencia física de pareja"),
]


def _or(res: dict, termino: str) -> tuple[float, float, float]:
    t = res["tabla_or"].set_index("termino").loc[termino]
    return float(t["or"]), float(t.ic_inf), float(t.ic_sup)


def _rp(df, predictores, termino, donde=None) -> float:
    t = mod.razon_prevalencias_diseno(df, "depresion_bin", predictores, REFERENCIAS, donde)
    return float(t.set_index("termino").loc[termino, "rp"])


def _cambio(sin: float, con: float) -> float:
    return (con - sin) / sin * 100


# ─────────────────────────────────────────────────────────────────────
# 1 · La altitud como confusor de los demás factores
# ─────────────────────────────────────────────────────────────────────


def confusion_por_altitud(base: pd.DataFrame) -> pd.DataFrame:
    """Compara cada OR (y RP) sin y con ajuste por piso altitudinal.

    La altitud entra como piso, no como recta: la relación con la depresión
    tiene forma de J, y una recta no controlaría bien el confusor. La
    comparación principal es entre el modelo logístico principal y ese mismo
    modelo con la altitud añadida. Como la región natural sale de la altitud,
    se repite la comparación sin región natural, que es el control menos
    solapado con la exposición.
    """
    filas = []
    d = base.dropna(subset=["depresion_bin", "altitud_categoria", *COMPLETO]).copy()
    sin_region = [v for v in COMPLETO if v != "region_natural"]

    def ajustar(df, preds, donde=None):
        return mod.logistica(df, "depresion_bin", preds, con_diseno=True,
                             referencias=REFERENCIAS, donde=donde)

    m_sin = ajustar(d, COMPLETO)
    m_con = ajustar(d, [*COMPLETO, "altitud_categoria"])
    m_sin_r = ajustar(d, sin_region)
    m_con_r = ajustar(d, [*sin_region, "altitud_categoria"])

    # Violencia: subpoblación con pareja, como en la tabla 27
    dv = base[base.tuvo_pareja == 1].dropna(
        subset=["depresion_bin", "altitud_categoria", *COMPLETO, "violencia_fisica"]).copy()
    mv_sin = ajustar(dv, [*COMPLETO, "violencia_fisica"])
    mv_con = ajustar(dv, [*COMPLETO, "violencia_fisica", "altitud_categoria"])

    for v, etq in EXPOSICIONES:
        if v == "violencia_fisica":
            muestra, n = dv, len(dv)
            sin, con = mv_sin, mv_con
            sin_r, con_r = None, None
            preds_sin, preds_con = [*COMPLETO, v], [*COMPLETO, v, "altitud_categoria"]
        else:
            muestra, n = d, len(d)
            sin, con, sin_r, con_r = m_sin, m_con, m_sin_r, m_con_r
            preds_sin, preds_con = COMPLETO, [*COMPLETO, "altitud_categoria"]

        crudo = _or(ajustar(muestra, [v]), v)
        solo_alt = _or(ajustar(muestra, [v, "altitud_categoria"]), v)
        o_sin, l_sin, u_sin = _or(sin, v)
        o_con, l_con, u_con = _or(con, v)
        rp_sin = _rp(muestra, preds_sin, v)
        rp_con = _rp(muestra, preds_con, v)

        cambio = _cambio(o_sin, o_con)
        fila = {
            "exposicion": etq, "variable": v, "n": n,
            "or_crudo": crudo[0], "or_solo_altitud": solo_alt[0],
            "cambio_crudo_solo_altitud_pct": _cambio(crudo[0], solo_alt[0]),
            "or_sin_altitud": o_sin, "sin_ic_inf": l_sin, "sin_ic_sup": u_sin,
            "or_con_altitud": o_con, "con_ic_inf": l_con, "con_ic_sup": u_con,
            "cambio_pct": cambio,
            "rp_sin_altitud": rp_sin, "rp_con_altitud": rp_con,
            "cambio_rp_pct": _cambio(rp_sin, rp_con),
            "cruza_el_1_sin": l_sin <= 1 <= u_sin, "cruza_el_1_con": l_con <= 1 <= u_con,
        }
        if sin_r is not None:
            os_r, ls_r, us_r = _or(sin_r, v)
            oc_r, lc_r, uc_r = _or(con_r, v)
            fila.update({"or_sin_altitud_sin_region": os_r, "or_con_altitud_sin_region": oc_r,
                         "cambio_sin_region_pct": _cambio(os_r, oc_r)})
        else:
            fila.update({"or_sin_altitud_sin_region": np.nan,
                         "or_con_altitud_sin_region": np.nan,
                         "cambio_sin_region_pct": np.nan})
        filas.append(fila)

    out = pd.DataFrame(filas)
    out["confunde"] = out.cambio_pct.abs() >= UMBRAL_CONFUSION

    def veredicto(r) -> str:
        if r.confunde:
            return "La altitud confunde: se reporta el OR ajustado por altitud"
        if abs(r.cambio_crudo_solo_altitud_pct) >= UMBRAL_CONFUSION:
            return ("Con el modelo principal no confunde (la región ya recoge la altitud); "
                    "sí cambia el OR crudo al ajustar solo por altitud")
        return "No confunde: el OR cambia menos de 10 %"

    out["veredicto"] = out.apply(veredicto, axis=1)
    return out


# ─────────────────────────────────────────────────────────────────────
# 2 · La altitud, cruda y ajustada por bloques
# ─────────────────────────────────────────────────────────────────────


def _con_educacion_4(preds: list[str]) -> list[str]:
    """Sustituye ``educacion_grupo`` por ``educacion_4`` en una lista de covariables."""
    return ["educacion_4" if v == "educacion_grupo" else v for v in preds]


def altitud_escalonada(base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Asociación de la altitud con la depresión, añadiendo ajustes por pasos.

    La cadena principal (pasos 1 a 6) se estima sobre casos completos, igual que
    la tabla 38, y reproduce sus filas (a), (b) y (c). Todos los pasos comparten
    muestra, para que lo que cambie entre filas sea el ajuste y no las personas.

    Esa muestra excluye a quienes nunca asistieron a la escuela, que tienen el
    nivel educativo nulo por salto del cuestionario y viven más alto que el
    resto. Por eso la cadena se repite incluyéndolos como una categoría más
    («Sin educación»): son las filas marcadas con asterisco.
    """
    base = sens.educacion_cuatro_niveles(base)
    comunes = ["depresion_bin", "altitud_km", "altitud_categoria", "departamento", "region_natural"]
    d = base.dropna(subset=[*comunes, *AJUSTE_ALTITUD]).copy()
    d4 = base.dropna(subset=[*comunes, *_con_educacion_4(AJUSTE_ALTITUD)]).copy()

    pasos = [
        ("(1) Sin ajustar", [], False),
        ("(2) + sexo y edad", ["es_mujer", "grupo_etario"], False),
        ("(3) + educación y área", ["es_mujer", "grupo_etario", "educacion_grupo", "es_rural"], False),
        ("(4) + conductas y condiciones clínicas", AJUSTE_ALTITUD, False),
        ("(5) + región natural (derivada de la altitud)", [*AJUSTE_ALTITUD, "region_natural"], False),
        ("(6) + departamento", [*AJUSTE_ALTITUD, "departamento"], False),
        ("(1*) Sin ajustar, con quienes no asistieron a la escuela", [], True),
        ("(4*) Como (4), con quienes no asistieron a la escuela", AJUSTE_ALTITUD, True),
        ("(6*) Como (6), con quienes no asistieron a la escuela",
         [*AJUSTE_ALTITUD, "departamento"], True),
    ]
    filas = []
    for nombre, extra, con_sin_educ in pasos:
        muestra = d4 if con_sin_educ else d
        preds = _con_educacion_4(extra) if con_sin_educ else extra
        r = mod.logistica(muestra, "depresion_bin", ["altitud_km", *preds], con_diseno=True,
                          referencias=REFERENCIAS)
        o, lo, hi = _or(r, "altitud_km")
        p = float(r["tabla_or"].set_index("termino").loc["altitud_km", "p"])
        filas.append({"modelo": nombre, "n": r["n"], "or_por_1000m": o,
                      "ic_inf": lo, "ic_sup": hi, "p": p, "or_por_100m": o ** 0.1,
                      "incluye_sin_educacion": con_sin_educ})
    pasos_df = pd.DataFrame(filas)
    pasos_df["lectura"] = np.where(pasos_df.ic_inf > 1, "El IC no cruza 1: el gradiente se mantiene",
                                   "El IC cruza 1: no se distingue de la ausencia de gradiente")

    # Pisos: cruda, ajustada del bloque (4) y con departamento (6), con y sin los
    # que no asistieron a la escuela
    filas_pisos = []
    for nombre, extra, con_sin_educ in [
        ("Sin ajustar", [], False), ("Ajustada (4)", AJUSTE_ALTITUD, False),
        ("Ajustada (6), con departamento", [*AJUSTE_ALTITUD, "departamento"], False),
        ("Ajustada (4*), incluye sin educación", AJUSTE_ALTITUD, True),
        ("Ajustada (6*), con departamento, incluye sin educación",
         [*AJUSTE_ALTITUD, "departamento"], True),
    ]:
        muestra = d4 if con_sin_educ else d
        preds = _con_educacion_4(extra) if con_sin_educ else extra
        r = mod.logistica(muestra, "depresion_bin", ["altitud_categoria", *preds],
                          con_diseno=True, referencias=REFERENCIAS)
        t = r["tabla_or"]
        t = t[t.termino.str.startswith("altitud_categoria_")]
        for _, f in t.iterrows():
            filas_pisos.append({
                "modelo": nombre, "piso": f.termino.replace("altitud_categoria_", ""),
                "or": f["or"], "ic_inf": f.ic_inf, "ic_sup": f.ic_sup, "p": f.p})
    return pasos_df, pd.DataFrame(filas_pisos)


# ─────────────────────────────────────────────────────────────────────
# 3 · Ecológico frente a individual
# ─────────────────────────────────────────────────────────────────────


def ecologico_vs_individual(base: pd.DataFrame, pasos: pd.DataFrame) -> pd.DataFrame:
    """Pone la correlación departamental junto a la estimación individual."""
    d = base.dropna(subset=["depresion_bin", "altitud"]).copy()
    g = d.groupby("departamento").apply(
        lambda x: pd.Series({"alt": x.altitud.mean() / 1000,
                             "prev": np.average(x.depresion_bin, weights=x.peso) * 100}),
        include_groups=False)
    r, p_r = stats.pearsonr(g.alt, g.prev)
    rho, p_rho = stats.spearmanr(g.alt, g.prev)
    pend = stats.linregress(g.alt, g.prev)
    filas = [
        {"nivel": "Ecológico (25 departamentos)",
         "medida": "Correlación de Pearson entre altitud media y prevalencia",
         "valor": r, "detalle": f"p = {p_r:.4f}; Spearman = {rho:.3f} (p = {p_rho:.4f})"},
        {"nivel": "Ecológico (25 departamentos)",
         "medida": "Pendiente: puntos porcentuales de prevalencia por 1 000 m de altitud media",
         "valor": pend.slope,
         "detalle": f"IC 95 % {pend.slope - 1.96 * pend.stderr:.2f} a "
                    f"{pend.slope + 1.96 * pend.stderr:.2f}"},
    ]
    for nombre in ("(1) Sin ajustar", "(4) + conductas y condiciones clínicas", "(6) + departamento",
                   "(6*) Como (6), con quienes no asistieron a la escuela"):
        f = pasos[pasos.modelo == nombre].iloc[0]
        filas.append({"nivel": "Individual",
                      "medida": f"OR por 1 000 m, modelo {nombre}",
                      "valor": f.or_por_1000m,
                      "detalle": f"IC 95 % {f.ic_inf:.2f} a {f.ic_sup:.2f}; p = {f.p:.4f}"})
    return pd.DataFrame(filas)


# ─────────────────────────────────────────────────────────────────────
# 4 · Quién vive en la altura
# ─────────────────────────────────────────────────────────────────────


def perfil_por_altitud(base: pd.DataFrame) -> pd.DataFrame:
    """Compara quién vive a 2 500 m o más con quién vive por debajo de 1 500 m.

    Es lo que justifica tratar la altitud como posible confusor: si el perfil de
    las personas cambia con la altura, la altitud arrastra otras diferencias.
    Proporciones con los pesos de la encuesta.
    """
    d = base.copy()
    d["tramo"] = np.where(d.altitud >= 2500, "2 500 m o más",
                          np.where(d.altitud < 1500, "Menos de 1 500 m", "1 500 a 2 499 m"))
    d["primaria_o_menos"] = (d.educacion_grupo == "Primaria o menos").astype(float)
    d["sin_educacion"] = d.educacion_grupo.isna().astype(float)

    def prop(g: pd.DataFrame, col: str, solo_con_dato: bool = False) -> float:
        x = g[col]
        w = g.peso
        if solo_con_dato:
            ok = g.educacion_grupo.notna()
            x, w = x[ok], w[ok]
        return float(np.average(x, weights=w) * 100)

    filas = []
    for tramo, g in d.groupby("tramo"):
        filas.append({
            "tramo_altitud": tramo, "personas": len(g),
            "area_rural_pct": prop(g, "es_rural"),
            "primaria_o_menos_pct": prop(g, "primaria_o_menos", True),
            "sin_educacion_pct": prop(g, "sin_educacion"),
            "mujeres_pct": prop(g, "es_mujer"),
            "prevalencia_pct": prop(g, "depresion_bin"),
        })
    orden = ["Menos de 1 500 m", "1 500 a 2 499 m", "2 500 m o más"]
    return pd.DataFrame(filas).set_index("tramo_altitud").loc[orden].reset_index()


# ─────────────────────────────────────────────────────────────────────
# Figura
# ─────────────────────────────────────────────────────────────────────


def figura(conf: pd.DataFrame, pasos: pd.DataFrame) -> None:
    """Dos paneles: altitud como confusor y gradiente cruda frente a ajustada."""
    viz.aplicar_tema()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13.5, 5.6),
                                 gridspec_kw={"width_ratios": [1.15, 1]})

    d = conf.sort_values("or_sin_altitud")
    y = np.arange(len(d))
    for yi, (_, r) in zip(y, d.iterrows(), strict=False):
        col = COL["rojo"] if r.confunde else COL["gris"]
        a1.plot([r.or_sin_altitud, r.or_con_altitud], [yi, yi], color=col, linewidth=2, zorder=2)
    a1.scatter(d.or_sin_altitud, y, s=62, color=COL["navy"], label="Sin ajustar por altitud",
               zorder=3)
    a1.scatter(d.or_con_altitud, y, s=62, facecolor="white", edgecolor=COL["navy"],
               linewidth=1.8, label="Con altitud en el modelo", zorder=4)
    a1.axvline(1, color=COL["gris"], linestyle="--", linewidth=1.2)
    a1.set_xscale("log")
    a1.xaxis.set_minor_locator(NullLocator())
    a1.xaxis.set_minor_formatter(NullFormatter())
    a1.set_xticks([0.5, 1, 2, 3, 5, 8])
    a1.set_xticklabels(["0,5", "1", "2", "3", "5", "8"])
    a1.set_yticks(y)
    a1.set_yticklabels(d.exposicion, fontsize=9.3)
    a1.set_xlabel("OR ajustado (escala logarítmica)")
    a1.set_title("La altitud en el modelo mueve poco los demás factores")
    a1.legend(loc="lower right", fontsize=8.8)

    p = pasos[~pasos.incluye_sin_educacion].copy()
    yy = np.arange(len(p))[::-1]
    a2.errorbar(p.or_por_1000m, yy, xerr=[p.or_por_1000m - p.ic_inf, p.ic_sup - p.or_por_1000m],
                fmt="o", color=COL["navy"], capsize=3, markersize=7)
    a2.axvline(1, color=COL["gris"], linestyle="--", linewidth=1.2)
    a2.set_yticks(yy)
    a2.set_yticklabels([m.split(" (derivada")[0] for m in p.modelo], fontsize=9)
    a2.set_xlabel("OR por cada 1 000 m de altitud")
    a2.set_title("El gradiente de la altitud, sin ajustar y ajustado")

    cambio_max = conf.cambio_pct.abs().max()
    nota = ("Izquierda: ningún factor cambia 10 % o más al añadir la altitud (el mayor cambio es "
            f"{cambio_max:.1f} %)." if not conf.confunde.any() else
            "Izquierda: en rojo, los factores cuyo OR cambia 10 % o más al añadir la altitud.")
    viz.pie_de_figura(
        fig, f"Fuente: ENDES 2025 (INEI). Diseño muestral complejo. {nota} "
             "Derecha: IC 95 %, casos completos. Asociación, no causalidad.")
    fig.tight_layout()
    dio.guardar_figura(fig, "fig_20_altitud_confusor")
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────
# Orquestador
# ─────────────────────────────────────────────────────────────────────


def main() -> None:
    """Ejecuta el análisis de la altitud como confusor y como exposición."""
    dio.configurar_logging()
    df = pd.read_parquet(cfg.DATASET_FINAL)
    base = df[df.en_analisis == 1].dropna(subset=["depresion_bin", "altitud"]).copy()
    print(f"Población de análisis con altitud: {len(base):,}\n")

    conf = confusion_por_altitud(base)
    dio.guardar_tabla(conf, "tabla_59_altitud_confusor_de_otros_factores",
                      "OR de cada factor sin y con ajuste por altitud")
    print("=" * 120)
    print("¿CONFUNDE LA ALTITUD A LOS DEMÁS FACTORES? (cambio del 10 % en el estimador)")
    print("=" * 120)
    with pd.option_context("display.float_format", "{:.3f}".format, "display.width", 220):
        print(conf[["exposicion", "or_crudo", "or_solo_altitud", "or_sin_altitud",
                    "or_con_altitud", "cambio_pct", "cambio_sin_region_pct",
                    "cambio_rp_pct", "confunde"]].to_string(index=False))

    pasos, pisos = altitud_escalonada(base)
    dio.guardar_tabla(pasos, "tabla_60_altitud_cruda_vs_ajustada",
                      "Asociación de la altitud con la depresión, cruda y ajustada por pasos")
    dio.guardar_tabla(pisos, "tabla_61_altitud_pisos_cruda_vs_ajustada",
                      "OR por piso altitudinal, crudo y ajustado")
    print("\n" + "=" * 120)
    print("ALTITUD → DEPRESIÓN: DE CRUDA A AJUSTADA")
    print("=" * 120)
    with pd.option_context("display.float_format", "{:.3f}".format, "display.width", 220):
        print(pasos.to_string(index=False))
        print()
        print(pisos.to_string(index=False))

    eco = ecologico_vs_individual(base, pasos)
    dio.guardar_tabla(eco, "tabla_62_ecologico_vs_individual",
                      "Gradiente ecológico frente a gradiente individual")
    print("\n" + "=" * 120)
    print("ECOLÓGICO FRENTE A INDIVIDUAL")
    print("=" * 120)
    with pd.option_context("display.float_format", "{:.3f}".format, "display.width", 220,
                           "display.max_colwidth", 90):
        print(eco.to_string(index=False))

    perfil = perfil_por_altitud(base)
    dio.guardar_tabla(perfil, "tabla_67_quien_vive_en_altura",
                      "Perfil de quienes viven a distintas altitudes (pesos de la encuesta)")
    print("\n" + "=" * 120)
    print("QUIÉN VIVE EN LA ALTURA")
    print("=" * 120)
    with pd.option_context("display.float_format", "{:.1f}".format, "display.width", 200):
        print(perfil.to_string(index=False))

    figura(conf, pasos)
    print("\nAnálisis de la altitud como confusor completado.")


if __name__ == "__main__":
    main()
