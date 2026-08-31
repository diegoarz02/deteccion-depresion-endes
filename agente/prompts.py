"""Prompts del agente y plantillas deterministas del modo degradado.

Las plantillas no son un parche por si falla el modelo: son la garantía de que
el proyecto entero funciona sin depender de un proveedor externo. Se construyen
con las cifras reales, así que dicen lo mismo que diría el modelo, sin la
variación de estilo.
"""

from __future__ import annotations

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
1. Qué muestran los datos de este perfil: la probabilidad estimada y su incertidumbre.
2. Cómo se compara con la prevalencia nacional y con la de su departamento, si la hay.
3. Qué factores del perfil contribuyen y con qué magnitud, en lenguaje llano.
4. Qué dice la evidencia del estudio para un perfil así.
5. Qué NO puede decir este análisis: los límites del diseño, del autorreporte y del
   punto de corte.
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

Estimación del modelo:
- Probabilidad estimada: {probabilidad:.1f} %
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


def plantilla_determinista(prediccion: dict, perfil: dict, contexto: list[str]) -> str:
    """Redacta la interpretación sin modelo, con las cifras reales.

    Sigue la misma estructura de seis bloques que se le pide al modelo, para que
    el modo degradado no se note en el contenido, solo en el estilo.
    """
    p = prediccion["probabilidad_pct"]
    base = prediccion["prevalencia_nacional"] * 100
    razon = prediccion["razon_sobre_prevalencia"]
    categoria = prediccion["categoria_riesgo"]

    if razon >= 2.5:
        comparacion = f"en unas {_n(razon)} veces la prevalencia nacional"
    elif razon >= 1.2:
        comparacion = f"por encima de la prevalencia nacional, en {_n(razon)} veces"
    elif razon >= 0.85:
        comparacion = "en torno a la prevalencia nacional"
    else:
        comparacion = f"por debajo de la prevalencia nacional, en {_n(razon)} veces"

    factores = prediccion.get("factores_contribuyentes", [])
    if factores:
        nombres = [f["factor"].lower() for f in factores[:3]]
        texto_factores = (
            f"El factor que más contribuye a esta estimación es {nombres[0]}."
            if len(nombres) == 1 else
            "Los factores que más contribuyen son "
            + ", ".join(nombres[:-1]) + f" y {nombres[-1]}.")
    else:
        texto_factores = ("Ningún factor del perfil eleva de forma apreciable la "
                          "estimación respecto de la población general.")

    linea_contexto = " " + " ".join(contexto[:2]) if contexto else ""

    return (
        f"De cada cien personas con este perfil en el Perú, alrededor de {p:.0f} "
        f"presentarían sintomatología depresiva moderada o grave según el PHQ-9. "
        f"La cifra se sitúa {comparacion}, que es del {_n(base)} %. "
        f"{texto_factores}"
        f"{linea_contexto} "
        f"Conviene leerlo con sus límites: es un estudio transversal, que mide la "
        f"exposición y el resultado a la vez, así que describe asociación y no causa. "
        f"El PHQ-9 es un instrumento de tamizaje respondido por la propia persona, no un "
        f"diagnóstico clínico, y su punto de corte no está validado específicamente para "
        f"población peruana. "
        f"La categoría asignada es de riesgo {categoria}. Si algo de esto te resuena, "
        f"hablar con un profesional de salud mental es el paso que sí puede evaluar tu "
        f"situación."
    )


def cierre(disclaimer: str, linea: str, modo: str, auc: float | None = None) -> str:
    """Construye el bloque de cierre con disclaimer, ayuda y trazabilidad."""
    incertidumbre = ""
    if auc:
        incertidumbre = (
            f"\n\nSobre la incertidumbre: el modelo discrimina con un AUC de {_n(auc, 2)}, "
            f"lo que basta para ordenar poblaciones por riesgo pero no para clasificar "
            f"a una persona.")
    origen = {
        "degradado": ("Interpretación redactada con plantillas deterministas sobre las "
                      "cifras del modelo."),
        "llm": ("Interpretación redactada por un modelo de lenguaje y verificada por el "
                "control de seguridad."),
        "crisis": "Respuesta fija, revisada, sin intervención de ningún modelo generativo.",
    }.get(modo, "Interpretación generada automáticamente.")
    return (f"{incertidumbre}\n\n{disclaimer}\n\n{linea}\n\n"
            f"Fuente: ENDES 2025 (INEI), n = 30 226. {origen}")
