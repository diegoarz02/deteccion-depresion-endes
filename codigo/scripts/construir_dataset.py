"""Fase 1 — construcción del dataset único del proyecto.

Ejecuta el pipeline completo: lectura de los .sav, unión por HHID, auditoría
de calidad, limpieza de códigos, construcción de variables, definición de la
población de estudio y guardado de ``datos/final/data.parquet``.

A partir de aquí, todo el proyecto consume únicamente ese parquet.

Uso
---
    python codigo/scripts/construir_dataset.py
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402
from depresion import geo  # noqa: E402
from depresion import io as dio  # noqa: E402
from depresion import limpieza as lim  # noqa: E402
from depresion import variables as var  # noqa: E402

log = logging.getLogger("construir_dataset")


def titulo(t: str) -> None:
    """Imprime un separador de sección en el log."""
    log.info("")
    log.info("=" * 78)
    log.info(t)
    log.info("=" * 78)


def auditoria_calidad(df: pd.DataFrame, meta: dio.Metadatos) -> pd.DataFrame:
    """Genera la tabla de calidad de datos, una fila por variable."""
    filas = []
    for c in df.columns:
        s = df[c]
        fila = {
            "variable": c,
            "descripcion": meta.etiqueta(c)[:80],
            "tipo": str(s.dtype),
            "n_validos": int(s.notna().sum()),
            "pct_faltantes": round(s.isna().mean() * 100, 2),
            "n_unicos": int(s.nunique()),
        }
        if s.dtype.kind in "fi":
            fila.update({
                "minimo": float(s.min()) if s.notna().any() else np.nan,
                "maximo": float(s.max()) if s.notna().any() else np.nan,
                "media": round(float(s.mean()), 3) if s.notna().any() else np.nan,
            })
            vc = s.value_counts(normalize=True)
            fila["pct_categoria_modal"] = round(vc.iloc[0] * 100, 2) if len(vc) else np.nan
        filas.append(fila)
    out = pd.DataFrame(filas)
    out["bandera"] = np.select(
        [out.pct_faltantes > 30, out.get("pct_categoria_modal", pd.Series(0, index=out.index)) > 98,
         out.n_unicos <= 1],
        ["Faltantes > 30%", "Varianza casi nula (>98% en una categoría)", "Constante"],
        default="",
    )
    return out


def flujograma_strobe(df: pd.DataFrame) -> pd.DataFrame:
    """Construye el flujograma STROBE con el N de cada exclusión."""
    n0 = len(df)
    phq_ok = df.phq9_completo == 1
    n1 = int(phq_ok.sum())
    con_peso = phq_ok & df.peso.notna()
    n2 = int(con_peso.sum())

    claves = ["edad", "es_mujer", "educacion_grupo", "area", "region_natural"]
    completo = con_peso & df[claves].notna().all(axis=1)
    n3 = int(completo.sum())

    pasos = [
        ("Personas de 15 años a más en CSALUD01 2025", n0, 0, ""),
        ("Excluidos: PHQ-9 incompleto", n1, n0 - n1,
         "Entrevista ausente, rechazada, incompleta o por discapacidad (QSRESULT)"),
        ("Excluidos: sin ponderador Peso15_AMAS", n2, n1 - n2,
         "Sin factor de ponderación asignado; no pueden entrar al análisis con diseño complejo"),
        ("Población de análisis (covariables clave completas)", n3, n2 - n3,
         # Solo falta el nivel educativo, y no por omisión: QS24 filtra a QS25N, y quien
         # nunca asistió a la escuela (QS24 = 2) no tiene nivel aprobado. Se comprobó
         # contra el archivo original (sensibilidad.verificar_sin_educacion).
         "Nunca asistieron a la escuela: el nivel educativo no aplica (QS24 = 2). "
         f"Variables exigidas: {', '.join(claves)}"),
    ]
    return pd.DataFrame(pasos, columns=["etapa", "n", "excluidos", "motivo"])


def main() -> None:
    """Ejecuta el pipeline completo de la Fase 1."""
    dio.configurar_logging()
    cfg.crear_directorios()

    # ── 1. Lectura ────────────────────────────────────────────────
    titulo("1. LECTURA DE MICRODATOS")
    csalud, meta_cs = dio.leer_sav(cfg.ARCHIVO_CSALUD)
    rech0, meta_r0 = dio.leer_sav(cfg.ARCHIVO_RECH0)
    meta = meta_cs.combinar(meta_r0)

    # ── 2. Unión ──────────────────────────────────────────────────
    titulo("2. UNIÓN POR HHID")
    df = lim.unir_bases(csalud, rech0)
    log.info("Tras la unión: %s filas x %s columnas", f"{len(df):,}", df.shape[1])

    # ── 3. Auditoría de calidad ───────────────────────────────────
    titulo("3. AUDITORÍA DE CALIDAD")
    calidad = auditoria_calidad(df, meta)
    dio.guardar_tabla(calidad, "tabla_01_calidad_datos",
                      "Auditoría de calidad de los datos ENDES 2025")
    log.info("Variables con bandera: %s de %s",
             int((calidad.bandera != "").sum()), len(calidad))
    log.info("Duplicados por HHID+QSNUMERO: %s",
             int(df.duplicated(subset=[cfg.LLAVE, "QSNUMERO"]).sum()))

    # ── 4. Verificación de saltos ─────────────────────────────────
    titulo("4. VERIFICACIÓN DE LA LÓGICA DE SALTOS")
    saltos = lim.verificar_saltos(df)
    dio.guardar_tabla(saltos, "tabla_02_verificacion_saltos",
                      "Verificación empírica de la lógica de saltos del cuestionario")
    log.info("\n%s", saltos.to_string(index=False))
    if (saltos.violaciones > 0).any():
        log.error("Hay violaciones de salto: revisar antes de continuar.")

    # ── 5. Limpieza ───────────────────────────────────────────────
    titulo("5. LIMPIEZA DE CÓDIGOS")
    inventario = lim.inventariar_codigos_especiales(df, meta)
    dio.guardar_tabla(inventario, "tabla_03_inventario_codigos_8_9",
                      "Inventario de códigos 8 y 9 con su etiqueta real")

    df, _ = lim.corregir_qs711(df)
    df, bitacora = lim.limpiar_codigos_faltantes(df, meta)
    dio.guardar_tabla(bitacora, "tabla_03b_bitacora_limpieza_codigos",
                      "Bitácora de recodificación de códigos especiales")

    df, antro = lim.limpiar_antropometria(df)
    dio.guardar_tabla(antro, "tabla_03c_limpieza_antropometria",
                      "Códigos de no-medición en antropometría")

    # ── 6. Construcción de variables ──────────────────────────────
    titulo("6. CONSTRUCCIÓN DE VARIABLES")
    df = var.construir_todas(df, meta.valores(cfg.VAR_DEPARTAMENTO))

    # ── 6b. Georreferenciación ────────────────────────────────────
    titulo("6b. GEORREFERENCIACIÓN")
    df, bitacora_coord = geo.corregir_coordenadas(df)
    dio.guardar_tabla(bitacora_coord, "tabla_31_correccion_coordenadas",
                      "Corrección de coordenadas con campos intercambiados")
    log.info("\n%s", bitacora_coord.to_string(index=False))

    df = geo.descomponer_ubigeo(df)
    df = geo.construir_altitud(df)
    log.info("Pisos altitudinales:\n%s",
             df.altitud_categoria.value_counts().sort_index().to_string())

    try:
        val = geo.validar_contra_distrito(df)
        log.info("Validación espacial contra el distrito declarado: %s", val)
        (cfg.LOGS / "validacion_espacial.json").write_text(
            json.dumps(val, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log.warning("No se pudo validar contra el shapefile: %s", e)

    # ── 7. Población de estudio ───────────────────────────────────
    titulo("7. POBLACIÓN DE ESTUDIO — FLUJOGRAMA STROBE")
    flujo = flujograma_strobe(df)
    dio.guardar_tabla(flujo, "tabla_04_flujograma_strobe",
                      "Flujograma STROBE de conformación de la muestra")
    log.info("\n%s", flujo.to_string(index=False))

    df["en_analisis"] = (
        (df.phq9_completo == 1) & df.peso.notna()
    ).astype(int)

    # ── 8. Selección de columnas y guardado ───────────────────────
    titulo("8. DATASET FINAL")
    columnas = [
        # identificación y diseño
        cfg.LLAVE, "QSNUMERO", "peso", "conglomerado", "estrato", "tiene_peso", "en_analisis",
        # desenlace
        "phq9_score", "phq9_completo", "depresion_bin", "depresion_leve_bin", "phq9_categoria",
        *cfg.ITEMS_PHQ9,
        # sociodemográficas
        "edad", "edad_topeada", "grupo_etario", "sexo", "es_mujer",
        "educacion", "educacion_grupo",
        # geografía
        "departamento", "departamento_norm", "area", "es_rural",
        "region_natural", "dominio_inei",
        # georreferenciación (segunda corrida)
        "ubigeo", "cod_departamento", "cod_provincia", "cod_distrito",
        "longitud", "latitud", "coord_estado", cfg.VAR_CENTRO_POBLADO,
        "altitud", "altitud_categoria", "altitud_100m", "altitud_km", "gran_altitud",
        # conductuales
        "alcohol_alguna_vez", "consumo_alcohol_12m", "consumo_frecuente", "consumo_30d",
        "n_criterios_abuso", "alcohol_problematico",
        "n_criterios_dependencia", "alcohol_dependencia", "alcohol_categoria",
        "fuma_12m", "fuma_30d", "fuma_diario", "tabaco_categoria",
        # social
        "estado_pareja", "tuvo_pareja", "violencia_fisica", "violencia_objeto",
        "violencia_max", "violencia_severidad",
        # clínicas
        "peso_kg", "talla_cm", "imc", "imc_categoria", "obesidad",
        "perimetro_abdominal", "obesidad_abdominal",
        "presion_sistolica", "presion_diastolica", "hta_medida",
        "hta_dx", "diabetes_dx", "n_cronicas", "tiene_cronica",
        # atención
        "recibio_tratamiento_sm", "brecha_atencion",
    ]
    columnas = [c for c in columnas if c in df.columns]
    final = df[columnas].copy()

    etiquetas = {
        "reglas_de_construccion": var.REGLAS,
        "escala_phq9": {str(k): v for k, v in cfg.ESCALA_PHQ9.items()},
        "escala_violencia": {str(k): v for k, v in cfg.ESCALA_VIOLENCIA.items()},
        "categorias_phq9": [{"min": a, "max": b, "etiqueta": c} for a, b, c in cfg.CATEGORIAS_PHQ9],
        "variables_prohibidas_como_predictores": cfg.VARIABLES_CON_FUGA,
        "diseno_muestral": {
            "peso": cfg.VAR_PESO, "escala": cfg.ESCALA_PESO,
            "conglomerado": cfg.VAR_CONGLOMERADO, "estrato": cfg.VAR_ESTRATO,
            "es_factor_de_expansion": cfg.PESO_ES_FACTOR_EXPANSION,
        },
    }
    dio.guardar_dataset_final(final, etiquetas)

    # ── 9. Diccionario de variables ───────────────────────────────
    titulo("9. DICCIONARIO DE VARIABLES")
    dicc = []
    for c in final.columns:
        s = final[c]
        dicc.append({
            "variable": c,
            "tipo": str(s.dtype),
            "n_valido": int(s.notna().sum()),
            "pct_faltantes": round(s.isna().mean() * 100, 2),
            "categorias": (
                ", ".join(map(str, s.cat.categories))
                if isinstance(s.dtype, pd.CategoricalDtype)
                else (f"{s.min():.1f} a {s.max():.1f}" if s.dtype.kind in "fi" and s.notna().any() else "")
            ),
            "regla_de_construccion": var.REGLAS.get(c, ""),
        })
    dicc = pd.DataFrame(dicc)
    dio.guardar_tabla(dicc, "tabla_00_diccionario",
                      "Diccionario de variables del dataset analítico")

    titulo("FASE 1 COMPLETADA")
    log.info("Dataset: %s filas x %s columnas", f"{len(final):,}", final.shape[1])
    log.info("En análisis: %s", f"{int(final.en_analisis.sum()):,}")


if __name__ == "__main__":
    main()
