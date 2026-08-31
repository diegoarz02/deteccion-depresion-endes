# Diccionario de variables del dataset analítico

Generado por `codigo/scripts/generar_diccionario.py` a partir de `resultados/tablas/tabla_00_diccionario.csv`.
Fuente: `datos/final/data.parquet` (33 569 × 82).

La columna **regla de construcción** contiene la recodificación exacta aplicada; es la referencia para replicar el dataset en R o SPSS.

> ⚠️ **No usar como predictores de `depresion_bin`:** `QS702`, `QS703`, `QS704A`, `QS704B`, `QS704C`, `QS704D`, `QS704E`, `QS704F`, `QS704G`, `QS704H`, `QS704I`
> — son fuga de información. Por eso no están en el dataset.

## Desenlace

| Variable | Tipo | N válido | % faltantes | Categorías o rango | Regla de construcción |
|---|---|---:|---:|---|---|
| `phq9_score` | float64 | 30,401 | 9.44 | 0.0 a 27.0 | Suma de QS700A..QS700I (escala 0-3 cada uno). Solo si los 9 ítems están presentes; con cualquier ítem faltante -> NaN, sin imputar. |
| `phq9_completo` | int64 | 33,569 | 0.0 | 0.0 a 1.0 | 1 si los nueve ítems del PHQ-9 están presentes; 0 si falta alguno. Es la marca que separa el faltante estructural del aleatorio. |
| `depresion_bin` | Float64 | 30,401 | 9.44 | 0.0 a 1.0 | 1 si phq9_score >= 10; 0 si no. NaN si PHQ incompleto. |
| `depresion_leve_bin` | Float64 | 30,401 | 9.44 | 0.0 a 1.0 | 1 si phq9_score >= 5; 0 si no. |
| `phq9_categoria` | category | 30,401 | 9.44 | Mínima, Leve, Moderada, Moderadamente severa, Severa | Mínima 0-4 / Leve 5-9 / Moderada 10-14 / Mod-severa 15-19 / Severa 20-27. |
| `QS700A` | float64 | 30,401 | 9.44 | 0.0 a 3.0 | Ítem del PHQ-9: «Poco interés o placer en hacer las cosas». Escala 0-3, tal cual de la encuesta. |
| `QS700B` | float64 | 30,401 | 9.44 | 0.0 a 3.0 | Ítem del PHQ-9: «Se sintió deprimido(a), decaído(a) o sin esperanza». Escala 0-3, tal cual de la encuesta. |
| `QS700C` | float64 | 30,401 | 9.44 | 0.0 a 3.0 | Ítem del PHQ-9: «Problemas para dormir o dormir demasiado». Escala 0-3, tal cual de la encuesta. |
| `QS700D` | float64 | 30,401 | 9.44 | 0.0 a 3.0 | Ítem del PHQ-9: «Se sintió cansado(a) o con poca energía». Escala 0-3, tal cual de la encuesta. |
| `QS700E` | float64 | 30,401 | 9.44 | 0.0 a 3.0 | Ítem del PHQ-9: «Poco apetito o comer en exceso». Escala 0-3, tal cual de la encuesta. |
| `QS700F` | float64 | 30,401 | 9.44 | 0.0 a 3.0 | Ítem del PHQ-9: «Dificultad para poner atención o concentrarse». Escala 0-3, tal cual de la encuesta. |
| `QS700G` | float64 | 30,401 | 9.44 | 0.0 a 3.0 | Ítem del PHQ-9: «Moverse o hablar lento, o estar inquieto(a)». Escala 0-3, tal cual de la encuesta. |
| `QS700H` | float64 | 30,401 | 9.44 | 0.0 a 3.0 | Ítem del PHQ-9: «Pensamientos de hacerse daño». Escala 0-3, tal cual de la encuesta. No se analiza ni se publica como desenlace independiente (ética, §15.3); alimenta la detección de crisis del agente. |
| `QS700I` | float64 | 30,401 | 9.44 | 0.0 a 3.0 | Ítem del PHQ-9: «Se sintió mal consigo mismo(a) o fracasado(a)». Escala 0-3, tal cual de la encuesta. |

## Diseño muestral

| Variable | Tipo | N válido | % faltantes | Categorías o rango | Regla de construcción |
|---|---|---:|---:|---|---|
| `HHID` | object | 33,569 | 0.0 |  | Identificador del hogar en la ENDES. Con QSNUMERO forma la llave. |
| `QSNUMERO` | float64 | 33,569 | 0.0 | 1.0 a 14.0 | Número de orden de la persona dentro del hogar. |
| `peso` | float64 | 30,226 | 9.96 | 0.0 a 19.4 | Peso15_AMAS / 1,000,000 (ficha técnica ENDES 2025, pág. 12). Es un peso RELATIVO normalizado, no un factor de expansión: sirve para proporciones y errores estándar, no para totales poblacionales. |
| `conglomerado` | float64 | 33,569 | 0.0 | 4344.0 a 7601.0 | QHCLUSTER (UPM). |
| `estrato` | float64 | 33,569 | 0.0 | 1.0 a 250.0 | HV022, proveniente de RECH0. |
| `tiene_peso` | int64 | 33,569 | 0.0 | 0.0 a 1.0 | 1 si la persona tiene ponderador Peso15_AMAS asignado. Sin él no puede entrar al análisis con diseño complejo. |
| `en_analisis` | int64 | 33,569 | 0.0 | 0.0 a 1.0 | 1 si la persona tiene PHQ-9 completo y ponderador. Es la población de análisis del flujograma STROBE (n = 30 226). |

## Geografía y territorio

| Variable | Tipo | N válido | % faltantes | Categorías o rango | Regla de construcción |
|---|---|---:|---:|---|---|
| `ubigeo` | object | 33,569 | 0.0 |  | Código INEI de seis dígitos, rellenado con ceros a la izquierda. |
| `cod_departamento` | object | 33,569 | 0.0 |  | Dígitos 1-2 del UBIGEO. 25 unidades: 24 departamentos más la Provincia Constitucional del Callao. |
| `cod_provincia` | object | 33,569 | 0.0 |  | Dígitos 1-4 del UBIGEO. Acumulativo: el código de provincia solo es único dentro de su departamento. |
| `cod_distrito` | object | 33,569 | 0.0 |  | UBIGEO completo de seis dígitos, único a nivel nacional. |
| `departamento` | object | 33,569 | 0.0 |  | HV024 (etiquetas limpias; HV023 es idéntica pero trae espacios a la izquierda). |
| `departamento_norm` | object | 33,569 | 0.0 |  | Nombre del departamento sin tildes ni espacios sobrantes, para poder cruzarlo con los shapefiles. |
| `NOMCCPP` | object | 33,569 | 0.0 |  | Nombre del centro poblado, tal como viene en RECH0. No se usa en el análisis; se conserva para poder auditar casos concretos. |
| `longitud` | float64 | 33,569 | 0.0 | -81.3 a -68.7 | LONGITUDX del centro poblado, tras corregir los registros con los campos intercambiados. NaN si el punto cae fuera del Perú. |
| `latitud` | float64 | 33,569 | 0.0 | -18.2 a -2.5 | LATITUDY del centro poblado, con la misma corrección que longitud. |
| `coord_estado` | object | 33,569 | 0.0 |  | Trazabilidad de la corrección: correcta / corregida (campos intercambiados) / descartada (fuera del territorio) / sin dato. |
| `area` | object | 33,569 | 0.0 |  | HV025: 1=Urbano, 2=Rural. |
| `es_rural` | Float64 | 33,569 | 0.0 | 0.0 a 1.0 | 1 si el área de residencia es rural; 0 si urbana. |
| `region_natural` | category | 33,569 | 0.0 | Costa, Sierra, Selva | Derivada a nivel de conglomerado: Sierra si HV040 >= 1500 m; si no, Costa cuando el departamento pertenece a la vertiente occidental (Tumbes, Piura, Lambayeque, La Libertad, Áncash, Lima, Callao, Ica, Arequipa, Moquegua, Tacna); Selva en cualquier otro caso. |
| `dominio_inei` | category | 33,569 | 0.0 | Lima Metropolitana, Costa, Sierra, Selva | Lima Metropolitana si UBIGEO de provincia es 1501 (Lima) o 0701 (Callao); en caso contrario, la región natural. |

## Altitud

| Variable | Tipo | N válido | % faltantes | Categorías o rango | Regla de construcción |
|---|---|---:|---:|---|---|
| `altitud` | float64 | 33,569 | 0.0 | 1.0 a 4500.0 | HV040, altitud del conglomerado en metros sobre el nivel del mar. |
| `altitud_categoria` | category | 33,569 | 0.0 | Costa / selva baja (0-499 m), Yunga (500-1 999 m), Quechua (2 000-2 999 m), Suni (3 000-3 999 m), Puna (4 000 m o más) | Piso altitudinal de Pulgar Vidal: Costa/selva baja (0-499), Yunga (500-1 999), Quechua (2 000-2 999), Suni (3 000-3 999), Puna (4 000+). Ordinal. |
| `altitud_100m` | float64 | 33,569 | 0.0 | 0.0 a 45.0 | altitud / 100. El OR por metro sería ilegible (1,0001). |
| `altitud_km` | float64 | 33,569 | 0.0 | 0.0 a 4.5 | altitud / 1000, para los modelos que reportan por kilómetro. |
| `gran_altitud` | Float64 | 33,569 | 0.0 | 0.0 a 1.0 | 1 si altitud >= 2 500 m. El corte es el de la literatura sobre altitud y depresión, no un cuantil de esta muestra. |

## Confusor / sociodemográfica

| Variable | Tipo | N válido | % faltantes | Categorías o rango | Regla de construcción |
|---|---|---:|---:|---|---|
| `edad` | float64 | 30,435 | 9.34 | 15.0 a 97.0 | QS23 tal cual (15-97). El valor 97 es un tope: '97 o más años'. |
| `edad_topeada` | int64 | 33,569 | 0.0 | 0.0 a 1.0 | 1 si la edad declarada es 97, el tope de la encuesta ('97 o más años'). Marca que ese valor está censurado. |
| `grupo_etario` | category | 30,435 | 9.34 | 15-19, 20-29, 30-39, 40-49, 50-59, 60+ | 15-19 / 20-29 / 30-39 / 40-49 / 50-59 / 60+. |
| `sexo` | object | 30,435 | 9.34 |  | QS24 recodificada a etiquetas: 1 = Hombre, 2 = Mujer. |
| `es_mujer` | Float64 | 30,435 | 9.34 | 0.0 a 1.0 | 1 si sexo = Mujer; 0 si Hombre. NaN si el sexo falta. |
| `educacion` | category | 29,287 | 12.76 | Inicial, Primaria, Secundaria, Superior no univ., Superior univ., Postgrado | QS25 en sus cuatro niveles originales, como categoría ordenada. |
| `educacion_grupo` | category | 29,287 | 12.76 | Primaria o menos, Secundaria, Superior | QS25N agrupado: {0,1}=Primaria o menos, {2}=Secundaria, {3,4,5}=Superior. |

## Exposición conductual

| Variable | Tipo | N válido | % faltantes | Categorías o rango | Regla de construcción |
|---|---|---:|---:|---|---|
| `alcohol_alguna_vez` | Float64 | 30,416 | 9.39 | 0.0 a 1.0 | QS400 = Sí (consumió alcohol alguna vez en la vida). |
| `consumo_alcohol_12m` | Float64 | 30,413 | 9.4 | 0.0 a 1.0 | QS208 (1=Sí,2=No). Quien responde 'No' en QS206 (nunca bebió) se fija en 0. |
| `consumo_frecuente` | Float64 | 30,402 | 9.43 | 0.0 a 1.0 | QS209 = Sí (12 o más días en 12 meses). Quien no bebió en 12 meses se fija en 0. |
| `consumo_30d` | Float64 | 30,410 | 9.41 | 0.0 a 1.0 | QS402 = Sí (consumo en los últimos 30 días). Se fija en 0 para quienes no bebieron en 12 meses: es un salto de cuestionario, no un dato ausente. |
| `n_criterios_abuso` | float64 | 30,402 | 9.43 | 0.0 a 4.0 | Número de criterios de abuso satisfechos (0-4), evaluados con lógica OR sobre sus ítems: actividades (QS713), social (QS715), riesgo (QS716), legal (QS717). Filtrado por QS209==1; quien no llegó al bloque = 0 (no aplica -> 0). |
| `alcohol_problematico` | Float64 | 30,402 | 9.43 | 0.0 a 1.0 | 1 si n_criterios_abuso >= 2. |
| `n_criterios_dependencia` | float64 | 30,402 | 9.43 | 0.0 a 8.0 | Número de criterios de dependencia satisfechos (0-8) sobre QS719-QS729, agrupando por criterio y no por ítem: abstinencia = QS721 o QS722; 'más de lo previsto' = QS723 o QS724 o QS725. Esta agrupación es necesaria porque el cuestionario salta la pregunta siguiente cuando la anterior fue 'Sí' (el criterio ya quedó satisfecho): contar ítems en crudo penalizaría a los casos más graves. Filtrado por alguna de QS713-717 == Sí; quien no llegó = 0. |
| `alcohol_dependencia` | Float64 | 30,402 | 9.43 | 0.0 a 1.0 | 1 si n_criterios_dependencia >= 3. |
| `alcohol_categoria` | category | 30,413 | 9.4 | No consumió en 12 meses, Ocasional, Frecuente sin problemas, Consumo problemático | Resumen ordinal del patrón de consumo: sin consumo, consumo sin criterios, abuso, dependencia. |
| `fuma_12m` | Float64 | 30,413 | 9.4 | 0.0 a 1.0 | QS200 = Sí. |
| `fuma_30d` | Float64 | 30,410 | 9.41 | 0.0 a 1.0 | QS201 = Sí; quien no fumó en 12 meses se fija en 0 (no aplica -> 0). |
| `fuma_diario` | Float64 | 30,410 | 9.41 | 0.0 a 1.0 | QS202 = Sí; quien no fumó en 30 días se fija en 0. |
| `tabaco_categoria` | category | 30,413 | 9.4 | No fumó, Fumó en 12 meses, Fumador ocasional, Fumador diario | Resumen ordinal del consumo de tabaco: nunca, exfumador, ocasional, diario. |

## Exposición social

| Variable | Tipo | N válido | % faltantes | Categorías o rango | Regla de construcción |
|---|---|---:|---:|---|---|
| `estado_pareja` | category | 30,401 | 9.44 | Sin pareja, Con pareja | QS709: 1=Con pareja, 2=Sin pareja. Define la SUBPOBLACIÓN del análisis de violencia. |
| `tuvo_pareja` | Float64 | 30,401 | 9.44 | 0.0 a 1.0 | QS800 = Sí (tuvo alguna vez pareja). Define la subpoblación a la que se le pregunta por violencia. |
| `violencia_fisica` | Float64 | 19,841 | 40.89 | 0.0 a 1.0 | 1 si QS710 > 1 o QS711 > 1 (cualquier frecuencia distinta de 'Nunca'). Solo definida en la subpoblación con pareja; NaN para quien no tuvo pareja (no es un 0). QS711 se lee en escala 1-4 pese a que el diccionario del INEI etiqueta 8 y 9. |
| `violencia_objeto` | Float64 | 19,841 | 40.89 | 0.0 a 1.0 | 1 si la pareja lanzó un objeto más de una vez. Solo definida en quienes tuvieron pareja; NaN en el resto. |
| `violencia_max` | float64 | 19,841 | 40.89 | 1.0 a 4.0 | Máximo entre violencia por golpe y por objeto: el peor de los dos indicadores, no su suma. |
| `violencia_severidad` | category | 19,841 | 40.89 | Nunca, Rara vez (1-2 veces), A veces (3-5 veces), A menudo (6 o más veces) | Máximo de QS710 y QS711 en escala Nunca / Rara vez / A veces / A menudo. |

## Exposición clínica

| Variable | Tipo | N válido | % faltantes | Categorías o rango | Regla de construcción |
|---|---|---:|---:|---|---|
| `peso_kg` | float64 | 29,892 | 10.95 | 25.6 a 181.4 | QS900 en kilogramos, tras convertir a NaN los códigos de no-medición (>= 900). |
| `talla_cm` | float64 | 29,884 | 10.98 | 115.1 a 193.7 | QS901 en centímetros, con la misma limpieza de códigos. |
| `imc` | float64 | 29,884 | 10.98 | 13.9 a 70.0 | peso_kg / (talla_cm/100)^2, tras convertir a NaN los códigos de no-medición (>=900). Valores fuera de [12, 70] se descartan por implausibles. |
| `imc_categoria` | category | 29,884 | 10.98 | Bajo peso, Normal, Sobrepeso, Obesidad | Categoría de la OMS: bajo peso (< 18,5), normal (18,5-24,9), sobrepeso (25-29,9), obesidad (>= 30). |
| `obesidad` | Float64 | 29,884 | 10.98 | 0.0 a 1.0 | IMC >= 30.0. |
| `perimetro_abdominal` | float64 | 29,471 | 12.21 | 54.8 a 165.8 | QS903 en centímetros, con la misma limpieza. |
| `obesidad_abdominal` | Float64 | 29,471 | 12.21 | 0.0 a 1.0 | Perímetro abdominal >= 102 cm en hombres, >= 88 cm en mujeres. |
| `presion_sistolica` | float64 | 30,131 | 10.24 | 62.5 a 220.0 | Promedio de las dos tomas de presión sistólica. |
| `presion_diastolica` | float64 | 30,131 | 10.24 | 40.0 a 141.0 | Promedio de las dos tomas de presión diastólica. |
| `hta_medida` | Float64 | 30,131 | 10.24 | 0.0 a 1.0 | Promedio de las dos tomas: sistólica >= 140 o diastólica >= 90 mmHg. |
| `hta_dx` | Float64 | 30,412 | 9.4 | 0.0 a 1.0 | QS102 = Sí (diagnóstico autorreportado de hipertensión). |
| `diabetes_dx` | Float64 | 30,407 | 9.42 | 0.0 a 1.0 | QS109 = Sí (diagnóstico autorreportado de diabetes). |
| `n_cronicas` | Float64 | 30,432 | 9.34 | 0.0 a 3.0 | Suma de hta_dx, diabetes_dx y obesidad (0-3). |
| `tiene_cronica` | Float64 | 30,432 | 9.34 | 0.0 a 1.0 | 1 si n_cronicas >= 1 (al menos hipertensión, diabetes u obesidad). |

## Atención en salud

| Variable | Tipo | N válido | % faltantes | Categorías o rango | Regla de construcción |
|---|---|---:|---:|---|---|
| `recibio_tratamiento_sm` | Float64 | 30,392 | 9.46 | 0.0 a 1.0 | QS707 = Sí (recibió tratamiento profesional por depresión/tristeza en 12 meses). |
| `brecha_atencion` | Float64 | 2,027 | 93.96 | 0.0 a 1.0 | 1 - recibio_tratamiento_sm, calculada SOLO entre quienes tienen depresion_bin == 1. NaN para el resto. |
