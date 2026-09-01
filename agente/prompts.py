"""Prompts del agente y plantillas deterministas del modo degradado.

Las plantillas no son un parche por si falla el modelo: son la garantía de que
el proyecto entero funciona sin depender de un proveedor externo. Se construyen
con las cifras reales, así que dicen lo mismo que diría el modelo, sin la
variación de estilo.
"""

from __future__ import annotations

import hashlib

SISTEMA = """Eres un epidemiólogo que comunica resultados de un estudio a público general.
El estudio es transversal, sobre la ENDES 2025 del Perú (n = 30 226 personas de 15 años
a más), y mide sintomatología depresiva con el PHQ-9.

QUÉ ERES
Un intérprete de números poblacionales. Explicas qué significa una estimación de riesgo,
la comparas con la evidencia del estudio y orientas hacia ayuda profesional.

QUÉ NO ERES
No eres diagnosticador, ni terapeuta, ni consejero clínico.

PROHIBICIONES ABSOLUTAS
1. No digas nunca «usted tiene depresión» ni ninguna variante. Habla de «personas con
   este perfil» o «de cada cien personas así».
1b. **No adjudiques ninguna cifra a quien consulta.** Prohibidas: «tu probabilidad es X»,
   «tu riesgo es», «tienes un X %», «en tu caso la probabilidad», «tu riesgo personal».
   Di en su lugar: «en tu grupo la tasa observada fue X», «de cada cien personas con este
   perfil, X dieron positivo».
   El motivo es aritmético, no de estilo: de cada cien personas que el modelo señala como
   riesgo, unas 85 no dan positivo. Una cifra presentada como personal es falsa cinco de
   cada seis veces.
2. No recomiendes tratamientos, fármacos ni dosis. Jamás.
3. No menciones suicidio ni autolesión.
4. No prometas resultados ni afirmes certezas sobre lo que le pasará a nadie.
5. **No escribas ningún número de teléfono ni ninguna URL.** Los recursos de ayuda los
   añade el sistema desde un catálogo verificado. Si los inventas, la respuesta se
   bloquea entera.
6. **Usa solo las cifras que recibes en el contexto.** No calcules, no redondees hacia
   una cifra más redonda, no añadas datos de memoria. Si un número no está en el
   contexto, no aparece en tu texto.
7. Es un estudio transversal: puedes hablar de asociación, nunca de causa.

ESTRUCTURA DE LA RESPUESTA
Seis bloques, en este orden, en prosa continua y sin encabezados:
1. **El hecho observado primero**: cuántas personas de cada cien con un perfil parecido
   dieron positivo en la encuesta. Es un recuento, no un pronóstico, y así hay que decirlo.
2. Cómo se compara con la prevalencia nacional y con la de su departamento, si la hay.
3. Qué factores del perfil contribuyen y con qué magnitud, en lenguaje llano.
4. Qué dice la evidencia del estudio para un perfil así.
5. Qué NO puede decir este análisis. Aquí va lo importante: el modelo discrimina poco
   (AUC 0,67), señala mal cinco de cada seis veces, y describe grupos, no personas.
   No lo escondas ni lo suavices: es el contenido más útil de la respuesta.
6. Una frase que oriente a buscar ayuda profesional, sin dar datos de contacto.

TONO
Sereno y respetuoso. Sin alarmismo («riesgo altísimo», «preocupante») y sin falsa
tranquilidad («no se preocupe», «no es nada»). Español claro, 160-240 palabras.
Nada de muletillas: «más allá de», «es importante destacar», «cabe resaltar»,
«en el mundo actual».

ENCUADRE OBLIGATORIO
Incluye, con tus palabras, que esto es una estimación estadística de riesgo poblacional
con fines académicos y no un diagnóstico."""

USUARIO = """Perfil consultado:
{perfil}

DATO OBSERVADO EN LA ENCUESTA (empieza la respuesta por aquí):
{observado}

Estimación del modelo (NO es la probabilidad de quien consulta):
- Estimación para este perfil: {probabilidad:.1f} %
- Prevalencia nacional: {prevalencia:.1f} %
- Es {razon:.1f} veces la prevalencia nacional
- Categoría de riesgo: {categoria}
- Factores que más aportan: {factores}

Contexto epidemiológico del estudio:
{contexto}

Redacta la interpretación siguiendo las reglas. Recuerda: sin teléfonos, sin URLs, y
solo con las cifras que aparecen arriba."""

REESCRITURA = """El texto anterior fue rechazado por el control de seguridad.

MOTIVO: {motivo}

Reescríbelo corrigiendo exactamente ese problema y respetando todas las reglas.
Mantén las cifras intactas. Devuelve solo el texto corregido, sin explicaciones."""


def _n(valor: float, decimales: int = 1) -> str:
    """Formatea con la coma decimal del español.

    El texto del agente se lee en castellano; mezclar «3.2 veces» con «9,9 %» en
    el mismo párrafo delata que las cifras vienen de sitios distintos.
    """
    return f"{valor:.{decimales}f}".replace(".", ",")


#: Concordancia de la categoría con el sustantivo que la acompaña. «Prevalencia
#: alto» es un descuido que delata que la frase se armó por concatenación.
_CATEGORIA_FEMENINA = {"alto": "alta", "medio": "media", "bajo": "baja"}


def _miles(n: int) -> str:
    """Separador de miles con espacio fino, como manda el uso en español."""
    return f"{n:,}".replace(",", " ")


# ─────────────────────────────────────────────────────────────────────
# Variedad de las plantillas
# ─────────────────────────────────────────────────────────────────────
# Dos perfiles muy distintos compartían el 91 % del texto: cambiaba la cifra y
# el resto era idéntico. Un texto así se nota automático a la segunda lectura.
#
# La variedad se elige con una huella del propio perfil, no al azar. Así el
# mismo perfil produce siempre el mismo texto —hace falta para poder citarlo en
# un trabajo, y para que dos personas que comparan pantallas vean lo mismo— y
# perfiles distintos leen distinto.


def _huella(*partes) -> str:
    """Firma estable del perfil, para elegir siempre las mismas variantes.

    Se usa blake2b y no ``hash()``: el hash de las cadenas en Python cambia
    entre ejecuciones por la aleatorización de semilla, y el mismo perfil
    produciría un texto distinto en cada arranque del servidor.

    Tampoco vale sumar los códigos de los caracteres, que fue el primer intento:
    difunde tan mal que dos perfiles muy distintos caían en la misma clase de
    resto y elegían idénticas variantes en todos los bloques a la vez. Un hash
    criptográfico reparte de verdad.
    """
    return "|".join(str(x) for x in partes)


def _elegir(opciones: list[str], huella: str, bloque: str) -> str:
    """Toma una variante de forma estable y descorrelacionada entre bloques.

    El nombre del bloque entra en el hash, así que la elección de la apertura no
    dice nada sobre la del cierre. Con un simple desplazamiento —huella, huella+1,
    huella+2— sí lo decía: coincidir en un bloque implicaba coincidir en todos.
    """
    firma = hashlib.blake2b(f"{bloque}:{huella}".encode(), digest_size=8).digest()
    return opciones[int.from_bytes(firma, "big") % len(opciones)]


#: Cómo se enuncia el dato observado. Cambia el orden de la frase, no el
#: contenido: las cuatro dicen exactamente lo mismo.
APERTURAS_OBSERVADO = [
    "De cada cien personas del mismo {definido}, {n_pos} dieron positivo al tamizaje de "
    "sintomatología depresiva del PHQ-9 en la ENDES 2025",
    "La encuesta entrevistó a {muestra} personas del mismo {definido}: {n_pos} de cada cien "
    "dieron positivo al tamizaje de sintomatología depresiva del PHQ-9",
    "Entre quienes comparten {definido}, el tamizaje del PHQ-9 dio positivo en {n_pos} de "
    "cada cien personas entrevistadas en la ENDES 2025",
    "El dato observado es este: de las personas con el mismo {definido}, {n_pos} de cada "
    "cien dieron positivo al tamizaje del PHQ-9",
]

#: Cómo se recuerda que es un recuento y no un pronóstico.
RECUENTOS = [
    "Es un recuento de lo que se observó, no un pronóstico.",
    "No es una predicción: son personas contadas una por una en la encuesta.",
    "Sale de contar, no de estimar.",
    "Es lo que se midió, no lo que se espera.",
]

#: Cómo se introduce la estimación del modelo, que va en segundo plano.
MODELOS = [
    "El modelo, por su parte, calcula un {p} % para un perfil con estas características",
    "La estimación del modelo para este perfil es del {p} %",
    "Un modelo estadístico ajustado sobre las mismas entrevistas da {p} % para este perfil",
    "Al mismo perfil, el modelo le asigna un {p} %",
]

#: Cómo se presentan los factores que más pesan.
FACTORES = [
    "Los factores que más contribuyen son {lista}.",
    "Lo que más pesa en esa estimación: {lista}.",
    "Tres características tiran de la cifra hacia arriba: {lista}.",
    "El modelo se apoya sobre todo en {lista}.",
]

#: El recordatorio del diseño transversal.
DISENOS = [
    "Conviene leerlo con sus límites: es un estudio transversal, que mide la exposición y el "
    "resultado a la vez, así que describe asociación y no causa.",
    "Una advertencia de método: al medirse todo en el mismo momento, estos datos muestran qué "
    "va junto con qué, no qué causa qué.",
    "El diseño del estudio marca hasta dónde se puede leer: como exposición y resultado se "
    "recogen a la vez, hay asociación pero no relación de causa.",
    "Sobre lo que estas cifras no pueden decir: al ser un corte en el tiempo, señalan "
    "coincidencias, no causas.",
]

#: El recordatorio de qué es el PHQ-9.
INSTRUMENTOS = [
    "El PHQ-9 es un instrumento de tamizaje respondido por la propia persona, no un "
    "diagnóstico clínico, y su punto de corte no está validado específicamente para "
    "población peruana.",
    "El PHQ-9 lo responde cada persona sobre sí misma: identifica sintomatología, no "
    "enfermedad, y el umbral que se usa viene de estudios internacionales.",
    "Conviene recordar qué mide el PHQ-9: síntomas autorreportados en las dos últimas "
    "semanas. Es un tamizaje, no un diagnóstico, y su corte no se ha validado en el Perú.",
]

#: El techo del modelo, dicho de cuatro maneras.
TECHOS = [
    "Conviene además saber qué tan bien funciona el modelo: de cada cien personas que señala "
    "como riesgo, cerca de ochenta y cinco no dan positivo, y predecir que nadie tiene "
    "depresión acierta más veces que él.",
    "Sobre la precisión: de cada cien a las que el modelo señala, unas ochenta y cinco no dan "
    "positivo. Responder «nadie» a todo el mundo acierta más veces.",
    "Un dato que cambia cómo leer todo lo anterior: cuando el modelo marca riesgo, se "
    "equivoca cinco de cada seis veces. Distingue poblaciones, no personas.",
    "Y algo que conviene tener presente: el modelo acierta menos que responder «nadie» a todo "
    "el mundo. Sirve para comparar grupos, no para señalar a alguien.",
]

#: El cierre que orienta a ayuda profesional.
CIERRES = [
    "Si algo de esto te resuena, hablar con un profesional de salud mental es el paso que sí "
    "puede evaluar tu situación.",
    "Ninguna de estas cifras sabe cómo estás tú. Esa conversación es con alguien que pueda "
    "escucharte.",
    "Si te has reconocido en algo de lo que leíste, un profesional de salud mental sí puede "
    "mirar tu caso concreto.",
    "Para saber cómo estás tú hace falta otra cosa: hablarlo con alguien preparado para "
    "escucharlo.",
]


def plantilla_determinista(prediccion: dict, perfil: dict, contexto: list[str],
                           observado: dict | None = None) -> str:
    """Redacta la interpretación sin modelo, con las cifras reales.

    Sigue la misma estructura de seis bloques que se le pide al modelo, para que
    el modo degradado no se note en el contenido, solo en el estilo.

    Parameters
    ----------
    observado : dict, optional
        Tasa realmente observada en la encuesta para perfiles parecidos. Cuando
        existe, encabeza la respuesta: es un recuento, no un pronóstico, y la
        estimación del modelo pasa a segundo plano nombrada como lo que es.

    Notas
    -----
    La distinción no es de matiz. «De cada cien personas con este perfil
    entrevistadas en la ENDES, veinte dieron positivo» describe la muestra y se
    puede comprobar. Decir lo mismo de una salida del modelo presenta un cálculo
    como si fuera un conteo, que es justo el error que el reencuadre de esta
    aplicación vino a corregir.
    """
    p = prediccion["probabilidad_pct"]
    base = prediccion["prevalencia_nacional"] * 100
    categoria = prediccion["categoria_riesgo"]

    # La comparación con la prevalencia nacional se hace sobre la MISMA cifra
    # que se acaba de enunciar. Si se abre con el dato observado y a renglón
    # seguido se compara la estimación del modelo, el texto encadena dos números
    # distintos sin avisar, y el lector los toma por el mismo.
    referencia = observado["prevalencia"] if observado else p
    razon = referencia / base if base else 0.0

    if razon >= 2.5:
        comparacion = f"en unas {_n(razon)} veces la prevalencia nacional"
    elif razon >= 1.2:
        comparacion = f"por encima de la prevalencia nacional, en {_n(razon)} veces"
    elif razon >= 0.85:
        comparacion = "en torno a la prevalencia nacional"
    else:
        comparacion = f"por debajo de la prevalencia nacional, en {_n(razon)} veces"

    # La huella sale del propio perfil, así que el mismo perfil produce siempre
    # el mismo texto y dos perfiles distintos leen distinto.
    huella = _huella(prediccion.get("categoria_riesgo", ""), round(p, 1),
                     (observado or {}).get("definido_por", ""),
                     (observado or {}).get("n", 0))

    factores = prediccion.get("factores_contribuyentes", [])
    if factores:
        nombres = [f["factor"].lower() for f in factores[:3]]
        lista = (nombres[0] if len(nombres) == 1
                 else ", ".join(nombres[:-1]) + f" y {nombres[-1]}")
        texto_factores = (
            f"El factor que más contribuye a esta estimación es {lista}."
            if len(nombres) == 1
            else _elegir(FACTORES, huella, "factores").format(lista=lista))
    else:
        texto_factores = ("Ningún factor del perfil eleva de forma apreciable la "
                          "estimación respecto de la población general.")

    linea_contexto = " " + " ".join(contexto[:2]) if contexto else ""

    if observado:
        # La brecha entre lo observado y lo estimado se explica solo cuando es
        # grande. Señalarla cuando ambas cifras casi coinciden distrae con algo
        # que el lector no había notado.
        if p > observado["prevalencia"] * 1.6:
            matiz = (", por encima del recuento porque además tiene en cuenta las conductas "
                     "y condiciones marcadas, que ese recuento no distingue. ")
        elif p < observado["prevalencia"] * 0.6:
            matiz = ", bastante por debajo del recuento anterior. "
        else:
            matiz = ". "

        apertura = (
            _elegir(APERTURAS_OBSERVADO, huella, "apertura").format(
                definido=observado["definido_por"],
                n_pos=f"{observado['prevalencia']:.0f}",
                muestra=_miles(observado["n"]))
            + f" (intervalo de confianza del 95 %: {_n(observado['ic_inf'])} % a "
              f"{_n(observado['ic_sup'])} %, sobre {_miles(observado['n'])} personas). "
            + _elegir(RECUENTOS, huella, "recuento") + " "
            + _elegir(MODELOS, huella, "modelo").format(p=_n(p)) + matiz)
    else:
        apertura = (
            f"El modelo estima que, de cada cien personas con este perfil, alrededor de "
            f"{p:.0f} presentarían sintomatología depresiva moderada o grave según el "
            f"PHQ-9. Es una estimación, no un recuento: en la encuesta no hay suficientes "
            f"personas con esta combinación exacta como para contarlas directamente. ")

    return (
        f"{apertura}"
        f"La cifra se sitúa {comparacion}, que es del {_n(base)} %. "
        f"{texto_factores}"
        f"{linea_contexto} "
        f"{_elegir(DISENOS, huella, 'diseno')} "
        f"{_elegir(INSTRUMENTOS, huella, 'instrumento')} "
        f"{_elegir(TECHOS, huella, 'techo')} "
        f"El grupo descrito es de prevalencia {_CATEGORIA_FEMENINA.get(categoria, categoria)}. Si algo de esto te resuena, "
        f"hablar con un profesional de salud mental es el paso que sí puede evaluar tu "
        f"situación."
    )


def cierre(disclaimer: str, linea: str, modo: str, auc: float | None = None) -> str:
    """Construye el bloque de cierre con disclaimer, ayuda y trazabilidad."""
    incertidumbre = ""
    if auc:
        incertidumbre = (
            f"\n\nSobre la incertidumbre: el modelo discrimina con un AUC de {_n(auc, 2)}. "
            f"Puestas dos personas al azar, una con síntomas y otra sin ellos, acierta "
            f"cuál es cuál dos de cada tres veces. Basta para ordenar poblaciones por "
            f"riesgo; no para clasificar a nadie.")
    origen = {
        "degradado": ("Interpretación redactada con plantillas deterministas sobre las "
                      "cifras del modelo."),
        "llm": ("Interpretación redactada por un modelo de lenguaje y verificada por el "
                "control de seguridad."),
        "crisis": "Respuesta fija, revisada, sin intervención de ningún modelo generativo.",
    }.get(modo, "Interpretación generada automáticamente.")
    return (f"{incertidumbre}\n\n{disclaimer}\n\n{linea}\n\n"
            f"Fuente: ENDES 2025 (INEI), n = 30 226. {origen}")
