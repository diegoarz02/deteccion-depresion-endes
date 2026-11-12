"""Fase 2 · Sensibilidad: quienes nunca asistieron a la escuela.

El análisis de casos completos excluye a 1 145 personas con el nivel educativo
nulo. Se comprobó contra ``QS24`` del archivo original que no son faltantes al
azar sino un salto del cuestionario: nunca asistieron a la escuela. Este script
responde dos preguntas sin tocar el modelo principal:

1. ¿Quiénes son, y cuánto se parecen o se distinguen del resto?
2. ¿Cambian los OR del modelo principal si se las incluye como una categoría
   más («Sin educación»)?

Además describe, con datos y no con adjetivos, a las 3 168 personas que
respondieron el cuestionario de salud pero no tienen el PHQ-9 completo (resultado
de la entrevista, ``QSRESULT``) y cómo se distinguen de las 30 401 que sí lo
tienen. Eso es lo que permite razonar la dirección del sesgo de selección.

El resultado sirve para describir el sesgo de selección con números en lugar de
con adjetivos. No sustituye a la tabla 22: los coeficientes que sirve la API y
que cita el boletín siguen siendo los del modelo con casos completos.

Uso
---
    python codigo/scripts/analisis_14_sensibilidad_sin_educacion.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402
from depresion import encuesta as enc  # noqa: E402
from depresion import io as dio  # noqa: E402
from depresion import modelos as mod  # noqa: E402
from depresion import sensibilidad as sens  # noqa: E402

warnings.filterwarnings("ignore")

SOCIODEMOGRAFICAS = ["es_mujer", "grupo_etario", "educacion_grupo", "es_rural", "region_natural"]
CONDUCTUALES_CLINICAS = ["consumo_frecuente", "alcohol_problematico", "fuma_12m",
                         "hta_dx", "diabetes_dx", "obesidad"]
COMPLETO = SOCIODEMOGRAFICAS + CONDUCTUALES_CLINICAS
REFERENCIAS = {"grupo_etario": "30-39", "educacion_grupo": "Superior",
               "educacion_4": "Superior", "region_natural": "Costa"}

ETIQUETAS = {
    "es_mujer": "Sexo femenino", "es_rural": "Área rural",
    "consumo_frecuente": "Consumo frecuente de alcohol",
    "alcohol_problematico": "Consumo problemático de alcohol",
    "fuma_12m": "Fumó en 12 meses", "hta_dx": "Hipertensión diagnosticada",
    "diabetes_dx": "Diabetes diagnosticada", "obesidad": "Obesidad (IMC ≥ 30)",
    "grupo_etario_15-19": "Edad 15-19 (ref. 30-39)", "grupo_etario_20-29": "Edad 20-29 (ref. 30-39)",
    "grupo_etario_40-49": "Edad 40-49 (ref. 30-39)", "grupo_etario_50-59": "Edad 50-59 (ref. 30-39)",
    "grupo_etario_60+": "Edad 60+ (ref. 30-39)",
    "educacion_grupo_Primaria o menos": "Primaria o menos (ref. Superior)",
    "educacion_grupo_Secundaria": "Secundaria (ref. Superior)",
    "educacion_4_Primaria o menos": "Primaria o menos (ref. Superior)",
    "educacion_4_Secundaria": "Secundaria (ref. Superior)",
    "educacion_4_Sin educación": "Sin educación (ref. Superior)",
    "region_natural_Sierra": "Sierra (ref. Costa)", "region_natural_Selva": "Selva (ref. Costa)",
}


def describir_grupo(base: pd.DataFrame) -> pd.DataFrame:
    """Perfil del grupo sin educación frente al resto, con prevalencia de diseño."""
    d = sens.educacion_cuatro_niveles(base)
    d["sin_educacion"] = (d.educacion_4 == sens.SIN_EDUCACION).astype(float)
    sub = d[d.sin_educacion == 1]
    res = d[d.sin_educacion == 0]

    diseno = enc.crear_diseno(d, ["depresion_bin", "sin_educacion"])
    prev = enc.prevalencia(diseno, "depresion_bin", por="sin_educacion", con_deff=False)
    prev["sin_educacion"] = prev.sin_educacion.astype(float)
    p_si = prev[prev.sin_educacion == 1].iloc[0]
    p_no = prev[prev.sin_educacion == 0].iloc[0]
    total = enc.prevalencia(diseno, "depresion_bin", con_deff=False).iloc[0]

    def pct(s: pd.Series) -> float:
        return float(s.mean() * 100)

    filas = [
        ("Personas en el análisis", len(sub), len(res)),
        ("Mujeres (%)", pct(sub.es_mujer), pct(res.es_mujer)),
        ("Área rural (%)", pct(sub.es_rural), pct(res.es_rural)),
        ("Edad media (años)", float(sub.edad.mean()), float(res.edad.mean())),
        ("Edad de 60 años o más (%)", pct((sub.edad >= 60).astype(float)),
         pct((res.edad >= 60).astype(float))),
        ("Altitud media del conglomerado (m)", float(sub.altitud.mean()), float(res.altitud.mean())),
        ("Casos con tamizaje positivo (sin ponderar)", int(sub.depresion_bin.sum()),
         int(res.depresion_bin.sum())),
        ("Prevalencia ponderada (%)", float(p_si.est), float(p_no.est)),
        ("IC 95 % inferior", float(p_si.lci), float(p_no.lci)),
        ("IC 95 % superior", float(p_si.uci), float(p_no.uci)),
    ]
    out = pd.DataFrame(filas, columns=["indicador", "sin_educacion", "resto"])
    out.attrs["prevalencia_total"] = float(total.est)
    return out


def no_respuesta_phq9(completo: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Resultado de la entrevista de quienes no tienen PHQ-9, y su perfil.

    ``completo`` es el dataset con las 33 569 personas del cuestionario de salud
    (no solo las del análisis). ``QSRESULT`` no está en el dataset final, así que
    se lee del archivo original; si no está disponible, devuelve ``None``.
    """
    ruta = cfg.FUENTE_SAV / cfg.ARCHIVO_CSALUD
    if not ruta.exists():
        print(f"AVISO: no existe {ruta}; se omite la descripción de la no respuesta")
        return None
    import pyreadstat

    crudo, meta = pyreadstat.read_sav(str(ruta), apply_value_formats=False,
                                      usecols=["HHID", "QSNUMERO", "QSRESULT"])
    etiquetas = meta.variable_value_labels.get("QSRESULT", {})
    u = completo.merge(crudo, on=["HHID", "QSNUMERO"], how="left", validate="one_to_one")
    u["resultado"] = u.QSRESULT.map(lambda v: etiquetas.get(v, f"código {v}"))
    u["con_phq9"] = u.phq9_completo.astype(bool)

    cruce = (u.groupby(["resultado", "con_phq9"]).size().unstack(fill_value=0)
             .rename(columns={True: "con_phq9", False: "sin_phq9"}))
    for c in ("con_phq9", "sin_phq9"):
        if c not in cruce:
            cruce[c] = 0
    cruce["total"] = cruce.con_phq9 + cruce.sin_phq9
    cruce = cruce.reset_index().sort_values("sin_phq9", ascending=False)

    # Sexo, edad y nivel educativo salen del cuestionario de salud, que estas
    # personas no completaron: solo 34 de las 3 168 los tienen. Lo que sí se
    # conoce de todas viene del registro del hogar: área y altitud.
    def resumen(g: pd.DataFrame) -> pd.Series:
        return pd.Series({
            "personas": len(g),
            "area_rural_pct": g.es_rural.mean() * 100,
            "altitud_media_m": g.altitud.mean(),
            "altitud_2500_o_mas_pct": (g.altitud >= 2500).mean() * 100,
            "con_dato_de_sexo_y_edad": int(g.edad.notna().sum()),
        })

    perfil = u.groupby("con_phq9").apply(resumen, include_groups=False).T
    perfil.columns = ["sin_phq9" if not c else "con_phq9" for c in perfil.columns]
    perfil = perfil[["con_phq9", "sin_phq9"]].reset_index(names="indicador")
    return cruce, perfil


def comparar_modelos(base: pd.DataFrame) -> pd.DataFrame:
    """Compara el modelo principal con el que incluye «Sin educación»."""
    d4 = sens.educacion_cuatro_niveles(base)
    sin_educ = [v if v != "educacion_grupo" else "educacion_4" for v in COMPLETO]

    # Modelo principal tal cual (tabla 22), para que el cotejo sea contra lo publicado
    r0 = mod.logistica(base.dropna(subset=["depresion_bin", *COMPLETO]), "depresion_bin",
                       COMPLETO, con_diseno=True, referencias=REFERENCIAS)
    r1 = mod.logistica(d4.dropna(subset=["depresion_bin", *sin_educ]), "depresion_bin",
                       sin_educ, con_diseno=True, referencias=REFERENCIAS)

    t0 = r0["tabla_or"].assign(termino_n=lambda x: x.termino.str.replace("educacion_grupo", "educacion_4"))
    t1 = r1["tabla_or"]
    unido = t0[["termino_n", "or", "ic_inf", "ic_sup"]].merge(
        t1[["termino", "or", "ic_inf", "ic_sup"]], left_on="termino_n", right_on="termino",
        how="outer", suffixes=("_principal", "_con_sin_educacion"))
    unido["termino"] = unido.termino.fillna(unido.termino_n)
    unido["etiqueta"] = unido.termino.map(lambda t: ETIQUETAS.get(t, t))
    unido["cambio_pct"] = ((unido.or_con_sin_educacion - unido.or_principal)
                           / unido.or_principal * 100)
    unido["supera_10_pct"] = unido.cambio_pct.abs() >= 10
    unido["n_principal"] = r0["n"]
    unido["n_con_sin_educacion"] = r1["n"]
    return unido[["etiqueta", "termino", "or_principal", "ic_inf_principal", "ic_sup_principal",
                  "or_con_sin_educacion", "ic_inf_con_sin_educacion", "ic_sup_con_sin_educacion",
                  "cambio_pct", "supera_10_pct", "n_principal", "n_con_sin_educacion"]]


def main() -> None:
    """Ejecuta la sensibilidad sobre el nivel educativo faltante."""
    dio.configurar_logging()
    df = pd.read_parquet(cfg.DATASET_FINAL)
    base = df[df.en_analisis == 1].dropna(subset=["depresion_bin"]).copy()

    ver = sens.verificar_sin_educacion(base)
    print("Verificación contra QS24 del archivo original:")
    for k, v in ver.items():
        print(f"  {k}: {v}")
    if ver.get("verificado"):
        assert ver["salto_estructural"], "QS25N nulo no coincide con QS24 == 2"
        assert ver["nulas_en_analisis"] == ver["nulas_que_nunca_asistieron"]

    perfil = describir_grupo(base)
    dio.guardar_tabla(perfil, "tabla_63_perfil_sin_educacion",
                      "Quienes nunca asistieron a la escuela frente al resto")
    print("\n" + "=" * 100)
    print("PERFIL DE QUIENES NUNCA ASISTIERON A LA ESCUELA")
    print("=" * 100)
    with pd.option_context("display.float_format", "{:.2f}".format, "display.width", 160):
        print(perfil.to_string(index=False))
    print(f"Prevalencia ponderada del total: {perfil.attrs['prevalencia_total']:.2f} %")

    nr = no_respuesta_phq9(df)
    if nr is not None:
        cruce, perfil_nr = nr
        dio.guardar_tabla(cruce, "tabla_65_resultado_entrevista_phq9",
                          "Resultado de la entrevista según tenga o no PHQ-9 completo")
        dio.guardar_tabla(perfil_nr, "tabla_66_perfil_sin_phq9",
                          "Quienes no tienen PHQ-9 completo frente a quienes sí")
        print("\n" + "=" * 100)
        print("RESULTADO DE LA ENTREVISTA (QSRESULT) SEGÚN TENGA PHQ-9 COMPLETO")
        print("=" * 100)
        print(cruce.to_string(index=False))
        print()
        with pd.option_context("display.float_format", "{:.2f}".format, "display.width", 160):
            print(perfil_nr.to_string(index=False))

    # Quién fuma y quién bebe con frecuencia, por sexo: es lo que hace del sexo un
    # confusor de esas dos asociaciones (se relaciona con la exposición y con el desenlace).
    filas = []
    for v, etq in [("fuma_12m", "Fumó en los últimos 12 meses"),
                   ("consumo_frecuente", "Consumo frecuente de alcohol")]:
        for es_mujer, sexo in [(0, "Hombres"), (1, "Mujeres")]:
            g = base[(base.es_mujer == es_mujer)].dropna(subset=[v])
            filas.append({
                "exposicion": etq, "sexo": sexo, "personas": len(g),
                "prevalencia_exposicion_pct": float(np.average(g[v], weights=g.peso) * 100),
                "prevalencia_depresion_pct": float(np.average(g.depresion_bin, weights=g.peso) * 100),
            })
    por_sexo = pd.DataFrame(filas)
    dio.guardar_tabla(por_sexo, "tabla_68_exposicion_por_sexo",
                      "Prevalencia de tabaco y de consumo frecuente de alcohol por sexo")
    print("\n" + "=" * 100)
    print("EXPOSICIÓN POR SEXO (pesos de la encuesta)")
    print("=" * 100)
    with pd.option_context("display.float_format", "{:.2f}".format, "display.width", 160):
        print(por_sexo.to_string(index=False))

    comp = comparar_modelos(base)
    dio.guardar_tabla(comp, "tabla_64_modelo_con_sin_educacion",
                      "Modelo principal frente al modelo que incluye 'Sin educación'")
    print("\n" + "=" * 100)
    print("MODELO PRINCIPAL FRENTE AL MODELO CON «SIN EDUCACIÓN»")
    print("=" * 100)
    with pd.option_context("display.float_format", "{:.3f}".format, "display.width", 200):
        print(comp[["etiqueta", "or_principal", "or_con_sin_educacion", "cambio_pct",
                    "supera_10_pct"]].to_string(index=False))
    print(f"\nn principal = {comp.n_principal.iloc[0]:,} · n con sin educación = "
          f"{comp.n_con_sin_educacion.iloc[0]:,}")
    print(f"Términos que cambian 10 % o más: {int(comp.supera_10_pct.sum())} de {len(comp)}")
    print(f"Cambio absoluto máximo: {comp.cambio_pct.abs().max():.1f} % "
          f"(media {comp.cambio_pct.abs().mean():.1f} %)")
    print("\nSensibilidad completada.")


if __name__ == "__main__":
    main()
