# =====================================================================
# Réplica en R de las tablas clave del análisis
# Proyecto: Detección de depresión en el Perú (ENDES 2025)
#
# Parte de datos/final/data.csv, el mismo dataset que consume el análisis
# en Python. El objetivo es que el docente pueda verificar los resultados
# con survey, que es la implementación de referencia para encuestas
# complejas y la que se espera en el curso.
#
# Uso:  Rscript codigo/R/analisis_equivalente.R
# =====================================================================

paquetes <- c("survey", "dplyr", "readr", "broom")
faltan <- paquetes[!paquetes %in% installed.packages()[, "Package"]]
if (length(faltan) > 0) install.packages(faltan, repos = "https://cloud.r-project.org")
invisible(lapply(paquetes, library, character.only = TRUE))

# Resuelve la raíz del proyecto tanto si se ejecuta con Rscript como desde
# RStudio, sin depender de operadores de versiones recientes de R.
args <- commandArgs(trailingOnly = FALSE)
arg_file <- grep("^--file=", args, value = TRUE)
este <- if (length(arg_file) > 0) sub("^--file=", "", arg_file[1]) else "codigo/R/x.R"
raiz <- normalizePath(file.path(dirname(este), "..", ".."), mustWork = FALSE)
ruta_datos <- file.path(raiz, "datos", "final", "data.csv")
salida <- file.path(raiz, "resultados", "tablas")

datos <- read_csv(ruta_datos, show_col_types = FALSE) |>
  filter(en_analisis == 1, !is.na(depresion_bin))

cat(sprintf("Población de análisis: %s\n\n", format(nrow(datos), big.mark = " ")))

# ---------------------------------------------------------------------
# 1. Declaración del diseño muestral
# ---------------------------------------------------------------------
# ENDES es bietápica, estratificada y por conglomerados. Las tres columnas
# son imprescindibles: omitir cualquiera da errores estándar mal calculados.
#
# 18 estratos tienen un solo conglomerado. La opción "adjust" centra esos
# estratos en la media general, que es el equivalente en R al tratamiento
# aplicado en Python (svy.singleton.center()).
options(survey.lonely.psu = "adjust")

diseno <- svydesign(
  ids     = ~conglomerado,   # unidad primaria de muestreo
  strata  = ~estrato,
  weights = ~peso,           # Peso15_AMAS / 1e6, ya escalado en el parquet
  data    = datos,
  nest    = TRUE             # conglomerados anidados dentro de estratos
)

cat("Diseño declarado:\n"); print(diseno); cat("\n")

# ---------------------------------------------------------------------
# 2. Prevalencia ponderada con IC 95 % y efecto de diseño
# ---------------------------------------------------------------------
# ATENCIÓN: el ponderador de ENDES es RELATIVO, no un factor de expansión.
# sum(peso) = 36 173, no la población peruana de 15+. Sirve para
# proporciones y errores estándar; NO para totales poblacionales.
cat(sprintf("Suma de pesos: %.1f  (no es la población: es un peso relativo)\n",
            sum(datos$peso)))

prev <- svyciprop(~I(depresion_bin == 1), diseno, method = "logit")
cat("\n--- Prevalencia nacional (PHQ-9 >= 10) ---\n")
print(prev); print(confint(prev))

# deff = "replace", no deff = TRUE. La opción por defecto compara contra un
# muestreo aleatorio simple SIN reemplazo y toma la suma de los ponderadores
# como tamaño de la población. Aquí esa suma es 36 173 —el peso es relativo,
# no un factor de expansión—, así que la corrección por población finita se
# calcula sobre una población falsa y devuelve un deff de 18,8, imposible para
# un diseño con conglomerados de este tamaño. Con "replace" la comparación es
# contra un MAS con reemplazo, que no necesita el tamaño poblacional, y el
# valor cae a ~3,1: el mismo que da svy en Python con deff="wr".
media_deff <- svymean(~depresion_bin, diseno, deff = "replace")
cat("\nEfecto de diseño:\n"); print(media_deff)
valor_deff <- as.numeric(attr(media_deff, "deff"))
cat(sprintf("Tamaño de muestra efectivo: %.0f\n\n", nrow(datos) / valor_deff))

# Se escriben a CSV para que la comparación con Python lea números, no texto
# formateado. Parsear la salida de consola de R funciona hasta que una tabla se
# parte en dos bloques por el ancho del terminal.
ic_prev <- confint(prev)
write.csv(
  data.frame(
    cantidad = c("Prevalencia nacional (%)", "IC inferior (%)", "IC superior (%)",
                 "Efecto de diseño", "Tamaño de muestra efectivo", "Suma de ponderadores",
                 "Conglomerados", "Población de análisis"),
    valor = c(as.numeric(prev) * 100, ic_prev[1] * 100, ic_prev[2] * 100,
              valor_deff, nrow(datos) / valor_deff, sum(datos$peso),
              length(unique(datos$conglomerado)), nrow(datos))),
  file.path(salida, "tabla_R_diseno.csv"), row.names = FALSE)

# ---------------------------------------------------------------------
# 3. Prevalencia por subgrupos
# ---------------------------------------------------------------------
cat("--- Prevalencia por subgrupo ---\n")
for (v in c("sexo", "grupo_etario", "educacion_grupo", "area", "region_natural")) {
  cat(sprintf("\n%s:\n", v))
  print(svyby(~depresion_bin, as.formula(paste0("~", v)), diseno, svymean,
              na.rm = TRUE, vartype = c("se", "ci")))
}

cat("\n--- Prevalencia por departamento ---\n")
print(svyby(~depresion_bin, ~departamento, diseno, svymean, na.rm = TRUE,
            vartype = c("se", "ci")) |> arrange(desc(depresion_bin)))

# ---------------------------------------------------------------------
# 4. Regresión logística con diseño complejo
# ---------------------------------------------------------------------
# Referencias fijadas igual que en Python, para que los OR sean comparables.
datos$grupo_etario    <- relevel(factor(datos$grupo_etario), ref = "30-39")
datos$educacion_grupo <- relevel(factor(datos$educacion_grupo), ref = "Superior")
datos$region_natural  <- relevel(factor(datos$region_natural), ref = "Costa")

diseno <- update(diseno,
                 grupo_etario    = relevel(factor(grupo_etario), ref = "30-39"),
                 educacion_grupo = relevel(factor(educacion_grupo), ref = "Superior"),
                 region_natural  = relevel(factor(region_natural), ref = "Costa"))

modelo <- svyglm(
  depresion_bin ~ es_mujer + grupo_etario + educacion_grupo + es_rural +
    region_natural + consumo_frecuente + alcohol_problematico + fuma_12m +
    hta_dx + diabetes_dx + obesidad,
  design = diseno,
  family = quasibinomial()   # quasi: evita el aviso de "non-integer #successes"
)

cat("\n--- Modelo logístico con diseño complejo ---\n")
print(summary(modelo))

or_tabla <- data.frame(
  termino = names(coef(modelo)),
  or      = exp(coef(modelo)),
  ic_inf  = exp(confint(modelo)[, 1]),
  ic_sup  = exp(confint(modelo)[, 2]),
  p       = summary(modelo)$coefficients[, 4]
)
cat("\n--- Odds ratios ajustados ---\n")
print(or_tabla, digits = 4)
write.csv(or_tabla, file.path(salida, "tabla_R_logistica.csv"), row.names = FALSE)

# ---------------------------------------------------------------------
# 5. Violencia de pareja: análisis de SUBPOBLACIÓN
# ---------------------------------------------------------------------
# Se usa subset() SOBRE EL OBJETO DE DISEÑO, nunca filter() sobre el data
# frame. Filtrar antes deja estratos y conglomerados vacíos y rompe el
# cálculo de la varianza.
sub_pareja <- subset(diseno, tuvo_pareja == 1)

cat("\n--- Violencia de pareja (subpoblación con pareja) ---\n")
print(svyciprop(~I(violencia_fisica == 1), sub_pareja, method = "logit"))

modelo_viol <- svyglm(
  depresion_bin ~ violencia_fisica + es_mujer + grupo_etario +
    educacion_grupo + es_rural + region_natural,
  design = sub_pareja, family = quasibinomial()
)
cat("\nOR ajustado de violencia física:\n")
print(exp(cbind(OR = coef(modelo_viol), confint(modelo_viol)))["violencia_fisica", ])

# ---------------------------------------------------------------------
# 6. ANOVA del puntaje PHQ-9
# ---------------------------------------------------------------------
# La versión con diseño complejo del contraste entre grupos.
cat("\n--- Contraste del PHQ-9 por grupo etario (con diseño) ---\n")
# El equivalente de un ANOVA bajo diseño complejo no es anova(): esa función
# compara dos modelos y con uno solo devuelve NULL sin avisar. La prueba
# correcta del bloque completo de un factor es el Wald ajustado por diseño,
# que es lo que hace regTermTest(). El ANOVA clásico supone independencia
# entre observaciones, y aquí las personas están agrupadas en conglomerados.
modelo_phq9 <- svyglm(phq9_score ~ grupo_etario, design = diseno)
print(regTermTest(modelo_phq9, ~grupo_etario, method = "Wald"))

cat("\n--- Medias del PHQ-9 por grupo etario ---\n")
print(svyby(~phq9_score, ~grupo_etario, diseno, svymean, na.rm = TRUE))

# ---------------------------------------------------------------------
# 7. Tabla de contingencia con prueba ajustada por diseño
# ---------------------------------------------------------------------
cat("\n--- Sexo por depresión (chi-cuadrado ajustado por diseño) ---\n")
print(svychisq(~sexo + depresion_bin, diseno, statistic = "F"))

cat("\n\nListo. Compara estos resultados con las tablas de resultados/tablas/.\n")
cat("Las diferencias deberían quedar en el cuarto decimal o más allá.\n")
