# Bitácora de decisiones metodológicas

Cada entrada registra **qué se decidió, por qué, y qué alternativa se descartó**.
Registrar el motivo de *inclusión* importa tanto como el de exclusión: sin eso, las
reincorporaciones de variables quedan huérfanas y son indefendibles ante un jurado.

---

## Fase 1 — Construcción del dataset

### `2026-08-30` — Lectura sin aplicar formatos de valor

**Decisión.** Leer los `.sav` con `pyreadstat.read_sav(..., apply_value_formats=False)`.

**Por qué.** `QS711` (violencia con objeto) tiene un error de etiquetado en el diccionario
del INEI: las etiquetas declaran los códigos 1, 2, 8 y 9, pero los datos graban 1, 2, 3 y 4.
Aplicar los formatos convertiría en `NaN` o en categoría sin nombre a los **33 casos de
violencia más severa**. Se conserva el código numérico y se aplica la escala ordinal 1-4 de
`QS710`, su pregunta gemela, que comparte la misma cartilla de respuesta en el cuestionario.

**Alternativa descartada.** Confiar en el diccionario oficial. Habría destruido el extremo
superior de la variable de exposición social más importante del estudio.

**Verificación.** `test_violencia_severa_preservada` exige que sobrevivan ≥33 casos.

---

### `2026-08-30` — Los códigos 8 y 9 se limpian variable por variable, nunca por convención

**Decisión.** Recodificar 8/9 a `NaN` **solo** cuando la etiqueta declara explícitamente
"No sabe", "No recuerda" o "Rehúsa". El resto queda intacto y se reporta.

**Por qué.** De las 127 variables con esos códigos, 87 se limpiaron y **40 quedaron
intactas**. Entre las intactas hay casos donde 8 y 9 son valores legítimos: `QSINTM` y
`QS22M` (8 = Agosto, 9 = Septiembre), `QS25AA` (8 = Achuar, 9 = Otra lengua nativa),
`QS25BB` (8 = Otro), y variables de conteo donde 8 y 9 son cantidades reales.

**Alternativa descartada.** La regla global "8 y 9 son faltantes". Habría corrompido meses
de entrevista, lengua materna y conteos.

**Evidencia.** `resultados/tablas/tabla_03_inventario_codigos_8_9.xlsx` y
`tabla_03b_bitacora_limpieza_codigos.xlsx`.

---

### `2026-08-30` — El `NaN` de un salto es "no aplica", y se codifica como tal

**Decisión.** Reconstruir cada variable siguiendo su filtro del cuestionario, codificando
el "no aplica" de forma explícita: quien nunca bebió tiene `0` criterios de abuso, no `NaN`;
quien no fumó en 12 meses tiene `fuma_diario = 0`.

**Por qué.** Un *complete-case* ingenuo sobre estas cadenas reduciría la muestra de ~30 000
a ~900 casos. Se verificaron los siete filtros contra los datos: **cero violaciones** (ningún
caso tiene dato presente sin cumplir su filtro), lo que confirma que los saltos son
estructurales y no no-respuesta.

**Excepción deliberada.** `violencia_fisica` **no** se codifica como 0 para quien no tuvo
pareja: no es "cero violencia", es una **subpoblación distinta** (n = 19 841 de 30 401). Se
analizará con el enfoque de *subpopulation analysis*, marcando la subpoblación sobre el
objeto de diseño en lugar de filtrar el data frame.

**Evidencia.** `resultados/tablas/tabla_02_verificacion_saltos.xlsx`.

---

### `2026-08-30` — Los criterios de alcohol se agrupan; no se cuentan ítems en crudo

**Decisión.** Construir `n_criterios_abuso` (0-4) y `n_criterios_dependencia` (0-8) con
lógica OR dentro de cada criterio, en lugar de sumar respuestas afirmativas ítem a ítem.

**Por qué.** El bloque tiene saltos del tipo *"si responde Sí, salta la siguiente"*:
`QS721 → QS722` y `QS723 → QS724 → QS725` solo se preguntan a quien respondió **No** a la
anterior, porque el criterio ya quedó satisfecho. Contar ítems en crudo trataría ese `NaN`
como "no cumple" y **penalizaría justamente a los casos más graves**. Los criterios agrupados
son: abstinencia = `QS721` o `QS722`; "más de lo previsto" = `QS723` o `QS724` o `QS725`.

El caso inverso también existe: `QS715` solo se pregunta si `QS714 == Sí`, verificado
empíricamente (406 presentes = 406 con `QS714 == 1`).

**Alternativa descartada.** `alcohol_problematico = ≥2 síntomas afirmativos del bloque`,
mezclando los dos niveles anidados. Además de la distorsión anterior, mezclaría denominadores
distintos: el nivel 1 tiene n = 3 197 y el nivel 2 n = 951.

---

### `2026-08-30` — La región natural se deriva por altitud, no por departamento

**Decisión.** `region_natural` se deriva **a nivel de conglomerado**: Sierra si
`HV040 ≥ 1500 m`; si no, Costa cuando el departamento pertenece a la vertiente occidental;
Selva en cualquier otro caso.

**Por qué.** ENDES no trae región natural (`HV023` y `HV024` son ambas departamento, idénticas
fila a fila al 100 %). Un mapeo departamento → región clasificaría mal a miles de hogares,
porque la altitud es **fuertemente bimodal** dentro de varios departamentos: Áncash tiene
42 % de conglomerados bajo 500 m y 55 % sobre 2 300 m; La Libertad 70 %/25 %; Arequipa
10 %/72 %.

**Validación.** La regla reproduce los casos conocidos: Loreto, Ucayali y San Martín 100 %
selva; Tumbes y Callao 100 % costa; Huancavelica y Apurímac 100 % sierra. Y recupera la selva
alta de Cajamarca (Jaén), Junín (Chanchamayo), Cusco (La Convención) y Puno (Sandia), que un
mapeo departamental borraría.

**Limitación declarada.** Es una aproximación geográfica, no la clasificación oficial por
distrito del INEI. Debe reportarse como variable derivada en la sección de métodos.

**Alternativa disponible.** `dominio_inei` de 4 categorías, que separa Lima Metropolitana
(provincias de Lima y Callao vía UBIGEO) del resto.

---

### `2026-08-30` — El ponderador sirve para proporciones, no para totales

**Decisión.** Usar `peso = Peso15_AMAS / 1 000 000` para prevalencias, medias, OR y errores
estándar. **No** reportar totales poblacionales absolutos sin recalibrar.

**Por qué.** La ficha técnica (pág. 12) confirma el divisor. Pero la suma de pesos escalados
es **36 172,81**, del orden del tamaño muestral y no de la población peruana de 15 años a más
(≈26 millones): un factor ~719 de diferencia. Es un peso **relativo normalizado** al estilo
DHS, no un factor de expansión.

**Consecuencia.** Frases como "X millones de peruanos con depresión" **no** son derivables de
este dataset. Si el boletín las necesita, hay que multiplicar la prevalencia ponderada por
una proyección poblacional externa del INEI y citarla explícitamente.

**Test corregido.** El criterio de aceptación propuesto originalmente ("la suma de pesos ≈
población de 15+") habría fallado. Se sustituyó por
`test_suma_de_pesos`, que verifica ≈36 173.

---

### `2026-08-30` — `QS702`, `QS703` y `QS704A–I` quedan excluidas como predictores

**Decisión.** Estas once variables **no entran** al dataset analítico como predictores de
`depresion_bin`.

**Por qué.** Son fuga de información estructural:

- `QS702` (dificultad funcional) se pregunta **exactamente** a quien marcó ≥1 síntoma en
  `QS700`. Su cobertura es 49,46 %, idéntica al 49,5 % con `phq9_score > 0`. La cobertura
  *es* el desenlace disfrazado.
- `QS703` es un tamizaje de síntomas depresivos de 12 meses: un proxy directo del desenlace.
- `QS704A–I` es una segunda batería PHQ-9 completa (12 meses) que cuelga de `QS703`, y por
  tanto hereda la fuga.

Incluirlas produciría un AUC alto y falso.

**Uso permitido.** Como descriptivos (severidad funcional entre quienes ya tienen síntomas)
y como análisis de sensibilidad (concordancia entre el PHQ-9 de 14 días y el de 12 meses).
Eso es otra pregunta de investigación y debe declararse como tal.

**Test.** `test_no_hay_variables_con_fuga`.

---

### `2026-08-30` — El umbral 999,9 se aplica solo a la antropometría

**Decisión.** Convertir a `NaN` los valores `≥ 900` en `QS900` (peso), `QS901` (talla) y
`QS907` (perímetro abdominal). **No** aplicarlo a la presión arterial.

**Por qué.** Las cuatro variables de presión (`QS903S/D`, `QS905S/D`) no usan ese código: sus
rangos son plausibles (sistólica 61-220, diastólica 40-142 mmHg) y su faltante ya viene como
`NaN`. Aplicarles el filtro no habría hecho daño en esta ola, pero es una regla incorrecta que
fallaría silenciosamente ante un caso de hipertensión severa real.

**Verificación de escala.** Tras la limpieza, el IMC tiene media 27,50 y rango 13,9-70,0
(n = 29 884). La escala de peso y talla es correcta; no vienen multiplicados por 10.

**Alternativa complementaria.** Existen `QS902`, `QS906` y `QS908` ("resultado de la
medición": Medido / No presente / Rechazo / Medido parcialmente). Es una vía más limpia y
documentada para excluir no-mediciones, y se contrastará contra el umbral numérico.

---

### `2026-08-30` — Población de análisis y estrategia de faltantes

**Decisión.** Análisis principal por casos completos. Población de análisis = 30 226
personas (`en_analisis == 1`).

**Flujograma STROBE.**

| Etapa | N | Excluidos | Motivo |
|---|---:|---:|---|
| Personas de 15+ en CSALUD01 2025 | 33 569 | — | — |
| Con PHQ-9 completo | 30 401 | 3 168 | Entrevista ausente, rechazada, incompleta o por discapacidad (`QSRESULT`) |
| Con ponderador | 30 226 | 175 | Sin `Peso15_AMAS`; no pueden entrar al análisis con diseño complejo |
| Con covariables clave completas | 29 081 | 1 145 | Faltantes en `educacion_grupo` |

**Sobre la imputación múltiple.** La única covariable clave con faltantes relevantes es
`educacion_grupo`, con **3,79 %** dentro de la población de análisis — por debajo del umbral
del 5 % que dispararía la exigencia de MICE. Se hará igualmente un análisis de sensibilidad
con imputación múltiple para verificar que las conclusiones no cambian, pero el análisis
principal es de casos completos.

**Ojo con `violencia_fisica`.** Su 34,7 % de "faltantes" **no es no-respuesta**: es el salto
estructural de quien no tuvo pareja. No se imputa. Se analiza como subpoblación.

---

## Pendientes de decisión

- Confirmar la fuente del GeoJSON de departamentos y citarla en el README.
- Decidir si el DAG causal trata `imc`/`obesidad` como confusor o como mediador de la
  relación entre conducta y depresión. Afecta a qué entra en el modelo ajustado.
- Definir el conjunto de ajuste por criterio de puerta trasera **antes** de correr la
  regresión logística, no después de ver los resultados.
