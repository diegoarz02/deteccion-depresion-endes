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
| Con covariables clave completas | 29 081 | 1 145 | Nunca asistieron a la escuela: el nivel educativo no aplica (`QS24 = 2`) |

**Nota.** Esos 1 145 son quienes nunca asistieron a la escuela: `QS24` («¿asistió a la escuela?»)
filtra a `QS25N` («nivel que aprobó»), y quien respondió «No» no tiene nivel aprobado. Se comprobó
contra el archivo original que las 1 145 nulas del análisis coinciden con ellos. Ver la entrada del
2026-11-11 más abajo.

**Sobre la imputación múltiple.** La única covariable clave con faltantes relevantes es
`educacion_grupo`, con **3,79 %** dentro de la población de análisis — por debajo del umbral
del 5 % que dispararía la exigencia de MICE. Se hará igualmente un análisis de sensibilidad
con imputación múltiple para verificar que las conclusiones no cambian, pero el análisis
principal es de casos completos.

**Ojo con `violencia_fisica`.** Su 34,7 % de "faltantes" **no es no-respuesta**: es el salto
estructural de quien no tuvo pareja. No se imputa. Se analiza como subpoblación.

---

## Fase 2 — Validación de resultados (noviembre de 2026)

Estas entradas documentan la validación de los resultados: medidas de asociación y riesgo atribuible,
sesgos, altitud como posible confusor y consistencia entre el boletín, la aplicación y el agente.
Ninguna cambia el modelo logístico principal ni los coeficientes que sirve la API.

### `2026-11-11` — En un corte transversal se usa la razón de prevalencias, no el riesgo relativo

**Decisión.** Donde antes podía leerse «riesgo relativo» o «veces más riesgo», se nombra la
**razón de prevalencias** (cociente de dos prevalencias) y el **odds ratio**. No se calcula riesgo
relativo porque exige incidencia, y la ENDES no sigue a nadie en el tiempo (Mann, 2003).

**Cómo se estima.** Sin ajuste, como cociente de proporciones con el error de Katz. Con ajuste,
por Poisson con enlace logarítmico (`svy.GLM`, familia Poisson), que con varianza robusta es el
estimador recomendado para razones de prevalencias (Zou, 2004; Barros y Hirakata, 2003). La función
es `modelos.razon_prevalencias_diseno`.

**Alternativa descartada.** Log-binomial: suele no converger y no aporta frente a Poisson con
varianza robusta.

### `2026-11-11` — Riesgo atribuible basado en prevalencia

**Decisión.** Se reportan tres medidas, siempre con la advertencia de que se apoyan en prevalencia
y no en incidencia, y de que solo equivalen a «casos evitables» si la asociación fuera causal y no
confundida:

1. diferencia de prevalencias entre expuestos y no expuestos;
2. fracción atribuible en expuestos, `(RP - 1) / RP`;
3. fracción atribuible poblacional, por la fórmula de Levin con medidas crudas
   (`Pe (RP - 1) / (1 + Pe (RP - 1))`) y por la de Miettinen con la RP ajustada
   (`Pc (RP - 1) / RP`, con `Pc` la proporción de casos expuestos) (Miettinen, 1974; Rockhill et
   al., 1998).

**Pesos.** Las fracciones poblacionales se calculan con los pesos de la encuesta: la prevalencia de
una exposición en la muestra no es la de la población (la muestra sobrerrepresenta el área rural).
La tabla 2×2 con celdas a, b, c, d sí cuenta personas sin ponderar, como corresponde a esa
presentación, y se acompaña de la prueba de Rao y Scott porque Pearson supone independencia.

**Intervalos.** Las fracciones son funciones no lineales de varias estimaciones, así que sus IC 95 %
salen de 1 000 réplicas del bootstrap de Rao y Wu (`n_h - 1` conglomerados por estrato con pesos
reescalados; estratos de un conglomerado sin cambios). La RP ajustada usa la varianza de Taylor de
`svy`; el control cruzado con el bootstrap da anchos equivalentes (cociente entre 0,8 y 1,25, lo
verifica una prueba).

**Dónde.** `codigo/scripts/analisis_12_asociacion_atribuible.py`; tablas 57 y 58.

### `2026-11-11` — La lectura de una 2×2 exige que sobreviva al diseño

La tabla 2×2 sin ponderar puede mostrar una señal que el diseño no sostiene, incluso de signo
contrario: en el área rural, el odds ratio sin ponderar es 1,14 (rural «de riesgo»), con pesos la
prevalencia rural y urbana es casi igual (6,8 % y 7,0 %) y la prueba de Rao y Scott da p = 0,70. Por
eso la columna de lectura declara asociación solo si Rao y Scott rechaza al 5 %.

### `2026-11-11` — La altitud se trata como exposición y como posible confusor

**Confusor de los demás factores.** Se compara el OR (y la RP) de cada exposición principal sin y con
el piso altitudinal en el modelo, con el criterio del cambio del 10 % (Maldonado y Greenland, 1993;
Mickey y Greenland, 1989). La altitud entra por pisos y no como recta, porque la relación tiene forma
de J. Resultado: **no confunde** a ninguno; el mayor cambio es 1,4 % con la región natural en el
modelo y 7,9 % (área rural) sin ella. Dónde: `analisis_13_altitud_confusor.py`, tabla 59.

**Gradiente propio.** Se ajusta por etapas (sociodemográficas, conductas y clínicas, región natural,
departamento). La cadena reproduce la tabla 38. El ajuste por **departamento** compara solo dentro
de cada departamento: el OR por 1 000 m pasa de 1,09 a 1,05 (IC 95 % 0,96 a 1,14). La región natural
se deriva de la altitud, así que adjuntarla es controlar por una versión gruesa de la exposición; se
reporta con esa advertencia y el departamento se usa como control más fino. Tablas 60 a 62 y 67.

**Falacia ecológica.** La correlación departamental (r = 0,63) se presenta junto con el gradiente
individual, y el texto la identifica como dato de grupo (Robinson, 1950/2009; Morgenstern, 1995).

### `2026-11-11` — Quienes nunca asistieron a la escuela

**Descripción.** Las 1 145 personas con `educacion_grupo` nula son quienes respondieron «No» a `QS24`.
Son en su mayoría mujeres de 60 años o más, del área rural y de altitudes mayores, con prevalencia
ponderada de 15,9 % frente a 6,7 % en el resto.

**Tratamiento.** El modelo principal se mantiene con casos completos: sus coeficientes son los que sirve
la API. Como análisis de sensibilidad se incluye «sin educación» como categoría
(`sensibilidad.educacion_cuatro_niveles`): ninguno de los 17 coeficientes comparables cambia un 10 %
o más (máximo 6,4 %) y la categoría tiene un OR de 2,07 frente a educación superior. El OR crudo de la
altitud sí depende de incluirlas (1,05 con casos completos frente a 1,09 con ellas). La correspondencia
con `QS24` se verifica contra el `.sav` original cuando está disponible (`verificar_sin_educacion`).
Tablas 63 y 64.

### `2026-11-12` — Se mantiene el modelo con casos completos como análisis principal

**Decisión.** El modelo principal sigue siendo el de casos completos (n = 28 553) y la inclusión de «sin
educación» queda como análisis de sensibilidad, ya presentado en el boletín (sección 12) y en las tablas 63 y 64.

**Razones.** (1) Ninguno de los 17 coeficientes comparables cambia un 10 % o más al incluirlas (máximo 6,4 %), de
modo que las conclusiones sobre los factores no dependen de esta elección. (2) Los coeficientes del modelo
principal son los que sirve la API y los que respaldan las cifras del boletín, de la aplicación y del agente;
cambiarlos al final movería a la vez la muestra, el AUC, el ranking SHAP y las tablas, sin cambiar lo que se
concluye. (3) El límite queda declarado: ese grupo tiene prevalencia más alta (15,9 % frente a 6,7 %) y no entra en
las estimaciones del modelo, y la aplicación lo avisa junto al selector de nivel educativo.

**Alternativa disponible.** Tratar «sin educación» como cuarta categoría del modelo principal también es defendible,
porque no es un dato perdido sino una respuesta válida. Está implementada en
`sensibilidad.educacion_cuatro_niveles`; adoptarla implicaría volver a correr las etapas de modelado, SHAP y
atribuibles y revisar las cifras de las tres superficies.

### `2026-11-11` — La no respuesta del PHQ-9 se describe con `QSRESULT`

De las 33 569 personas del cuestionario de salud, 3 168 no tienen el PHQ-9 completo: 777 ausentes,
899 rechazadas, 1 419 incompletas, 70 por discapacidad y 3 otras. Su sexo y su edad no figuran en
el archivo; por el registro del hogar se sabe que son más urbanas. No se puede decir hacia dónde
mueven la prevalencia. Tablas 65 y 66.

### `2026-11-11` — Referencias: una sola fuente

Las citas del boletín, su lista APA 7 y `docs/referencias.bib` salen del mismo módulo
(`codigo/scripts/referencias_boletin.py`), de modo que no puede haber una cita sin referencia ni una
referencia sin cita. Cada entrada se verificó abriéndola (metadatos con Crossref y PubMed; contenido
con el resumen o el texto) y el módulo guarda qué se comprobó de cada una.

### `2026-11-12` — La prevalencia de referencia de la API es la ponderada

Cada perfil se compara con la **prevalencia nacional ponderada** (6,98 %), la estimada con el diseño
de la encuesta, que es la misma que cita el boletín y que muestra el panel de la aplicación. Con ella
están calibradas las probabilidades de la logística con diseño. `Servicio` la toma de `contexto.json`
(`_alinear_prevalencia`); la media sin ponderar de la muestra del modelo queda guardada como
`prevalencia_muestra_modelo` y no se usa como referencia. De esa referencia salen la razón de
prevalencias frente al total y la categoría «alta, media o baja».

### `2026-11-11` — Consistencia entre las tres superficies

El encuadre nuevo (razón de prevalencias, asociación y no causa, una foto, el territorio describe
grupos, la altitud no es un factor aislado) se aplicó a la aplicación web (`api/web/`), a las
plantillas del modo degradado del agente (`agente/prompts.py`) y al texto de respaldo de
`/interpretar`. Los coeficientes servidos no cambian y `api/requirements.txt` sigue igual. El nodo
de crisis y su plantilla fija no se tocaron.

---

## Pendientes de decisión

- Confirmar la fuente del GeoJSON de departamentos y citarla en el README.
- Decidir si el DAG causal trata `imc`/`obesidad` como confusor o como mediador de la
  relación entre conducta y depresión. Afecta a qué entra en el modelo ajustado.
- Definir el conjunto de ajuste por criterio de puerta trasera **antes** de correr la
  regresión logística, no después de ver los resultados.
