"""Guardrail de seguridad clínica del agente.

El agente interpreta hallazgos **poblacionales**. Nunca diagnostica, nunca
recomienda fármacos, nunca se dirige a la persona como si fuera su paciente y
nunca inventa un dato de contacto.

Se implementa con reglas y no con un modelo, deliberadamente: un guardrail que
depende de una llamada de red falla justo cuando más falta hace, y no es
auditable. Estas reglas se pueden leer, discutir y probar — y hay tests que las
prueban.
"""

from __future__ import annotations

import re

# ── Lenguaje diagnóstico dirigido a la persona ────────────────────────
DIAGNOSTICO = [
    r"\busted (tiene|padece|sufre|presenta) (depresi[óo]n|un trastorno|una enfermedad)",
    r"\b(tienes|padeces|sufres) depresi[óo]n\b",
    r"\bte diagnostico\b", r"\ble diagnostico\b",
    r"\bsu diagn[óo]stico es\b", r"\btu diagn[óo]stico es\b",
    r"\best[áa] (usted )?deprimid[oa]\b",
    r"\bconfirma(mos)? (que|el) (tiene|diagn[óo]stico)",
    r"\bpadece de\b",
]

# ── Consejo médico o farmacológico ────────────────────────────────────
CONSEJO_MEDICO = [
    r"\b(debe|deber[íi]a|tiene que) (tomar|usar|consumir|iniciar) \w*\s*"
    r"(medicaci[óo]n|f[áa]rmac|antidepresiv)",
    r"\ble (receto|recetamos|prescribo|prescribimos)\b",
    r"\b(fluoxetina|sertralina|paroxetina|escitalopram|venlafaxina|amitriptilina|"
    r"citalopram|bupropi[óo]n|mirtazapina|alprazolam|clonazepam|diazepam)\b",
    r"\bdosis de\b", r"\bmiligramos\b", r"\bmg (al d[íi]a|diarios)\b",
    r"\bsuspenda (su|el) tratamiento\b",
    r"\bno necesita (ayuda|tratamiento|atenci[óo]n)\b",
]

# ── Contenido sensible sobre autolesión ───────────────────────────────
AUTOLESION = [
    r"\bsuicid", r"\bautolesi", r"\bquitarse la vida\b", r"\bhacerse da[ñn]o\b",
    r"\bmatarse\b", r"\bacabar con (su|tu) vida\b",
]

# ── Atribución de una cifra a la persona que consulta ─────────────────
# El fallo más sutil del sistema, y el que motivó el reencuadre de la
# aplicación: no decir «usted tiene depresión» —eso ya se bloquea— sino
# «tu probabilidad es del 19,9 %». Suena técnico y prudente, y sin embargo
# atribuye a una persona concreta una cifra que solo describe a un grupo.
#
# Con un valor predictivo positivo de 0,147, de cada cien personas señaladas
# como riesgo unas ochenta y cinco no dan positivo. Un número personal así, en
# salud mental, angustia a quien no lo necesita y tranquiliza a quien sí.
#
# Los patrones exigen la segunda persona (o el «usted») **junto a** una cifra o
# a la palabra probabilidad: hablar en segunda persona no es el problema, sino
# hacerlo para adjudicar un número.
ATRIBUCION_PERSONAL = [
    r"\b(tu|su) (probabilidad|riesgo|puntaje|porcentaje|estimaci[óo]n) (es|ser[íi]a|"
    r"asciende|alcanza|llega)",
    r"\b(tienes|tiene usted|usted tiene) (un |una )?\d+([.,]\d+)?\s*%",
    r"\b(tienes|tiene usted|usted tiene) (un |una )?(probabilidad|riesgo) de\b",
    r"\bt[úu] tienes (un |una )?\d",
    r"\b(tu|su) riesgo (personal|individual)\b",
    r"\bprobabilidad de que (t[úu]|usted) (tenga|tengas|desarrolle|desarrolles)\b",
    r"\ben tu caso,? (la|el) (probabilidad|riesgo|cifra)\b",
    r"\best[áa]s en (el|un) \d+([.,]\d+)?\s*%",
]

# ── Certeza indebida sobre un caso individual ─────────────────────────
CERTEZA = [
    r"\bseguro que (tiene|padece|desarrollar[áa])",
    r"\bcon (total )?certeza\b",
    r"\bsin duda (tiene|padece)\b",
    r"\bva a desarrollar\b",
    r"\bgarantiza(mos)?\b",
]

# ── URLs y teléfonos inventados ───────────────────────────────────────
# El modelo no puede emitir ningún dato de contacto que no esté en el catálogo
# verificado. Enviar a una persona a un enlace muerto o a un número equivocado
# es un daño real, y es justo el tipo de error que un modelo comete sin dar
# ninguna señal de que lo está cometiendo.
_URL = re.compile(r"https?://[^\s<>)\]]+|\bwww\.[^\s<>)\]]+", re.I)

# Secuencias de seis o más dígitos, admitiendo espacios y guiones internos.
# Los números cortos de emergencia se validan aparte: un patrón que capturase
# tres dígitos marcaría también cualquier cifra del análisis.
_TELEFONO = re.compile(r"\b(?:\+?51[\s-]?)?\d(?:[\s-]?\d){5,12}\b")

_COMP = {
    "diagnostico": [re.compile(p, re.I) for p in DIAGNOSTICO],
    "consejo_medico": [re.compile(p, re.I) for p in CONSEJO_MEDICO],
    "autolesion": [re.compile(p, re.I) for p in AUTOLESION],
    "certeza": [re.compile(p, re.I) for p in CERTEZA],
    "atribucion_personal": [re.compile(p, re.I) for p in ATRIBUCION_PERSONAL],
}

MOTIVOS = {
    "diagnostico": ("Lenguaje diagnóstico dirigido a la persona. El texto debe hablar de "
                    "riesgo poblacional estimado, nunca afirmar que alguien tiene depresión."),
    "consejo_medico": ("Consejo médico o mención de fármacos. El agente no prescribe ni "
                       "recomienda tratamientos: solo orienta a buscar ayuda profesional."),
    "autolesion": ("Mención de autolesión o suicidio. Es un tema que exige acompañamiento "
                   "clínico y no puede tratarse en una salida automática."),
    "certeza": ("Certeza indebida. Una probabilidad poblacional no permite afirmar qué le "
                "ocurrirá a una persona concreta."),
    "atribucion_personal": ("El texto adjudica una cifra a quien consulta («tu probabilidad "
                            "es X»). La cifra describe a un grupo, no a una persona: debe "
                            "reformularse como «en tu grupo la tasa observada fue X» o «de "
                            "cada cien personas con este perfil, X»."),
    "contacto_inventado": ("El texto incluye un teléfono o una URL que no está en el catálogo "
                           "verificado. Los datos de contacto solo pueden salir de "
                           "`agente/recursos_ayuda.json`."),
}

# Un texto poblacional válido debería mencionar la naturaleza estimada del dato.
SENALES_POBLACIONALES = [
    r"\bprobabilidad\b", r"\bestimad", r"\bprevalencia\b", r"\bpoblaci",
    r"\bde cada (cien|100)\b", r"\briesgo\b", r"\bpersonas con (este|un) perfil\b",
]


def _contactos_no_catalogados(texto: str) -> list[dict]:
    """Busca URLs y teléfonos que no estén en el catálogo verificado."""
    from recursos import telefonos_validos, urls_validas

    hallazgos = []

    permitidas = urls_validas()
    for m in _URL.finditer(texto):
        url = m.group(0).rstrip(".,;:")
        if not any(url.startswith(v) or v.startswith(url) for v in permitidas):
            hallazgos.append({"categoria": "contacto_inventado", "fragmento": url})

    permitidos = {t.replace(" ", "").replace("-", "") for t in telefonos_validos()}
    for m in _TELEFONO.finditer(texto):
        crudo = m.group(0).replace(" ", "").replace("-", "").lstrip("+")
        crudo = crudo[2:] if crudo.startswith("51") and len(crudo) > 9 else crudo
        if crudo not in permitidos:
            hallazgos.append({"categoria": "contacto_inventado", "fragmento": m.group(0)})
    return hallazgos


def verificar(texto: str) -> dict:
    """Analiza un borrador y decide si puede emitirse.

    Returns
    -------
    dict
        ``veredicto`` (``aprobado`` / ``reescribir`` / ``bloqueado``),
        ``motivo`` y la lista de ``coincidencias`` encontradas.
    """
    if not texto or not texto.strip():
        return {"veredicto": "reescribir", "motivo": "El borrador está vacío.",
                "coincidencias": []}

    hallazgos = []
    for categoria, patrones in _COMP.items():
        for p in patrones:
            m = p.search(texto)
            if m:
                hallazgos.append({"categoria": categoria, "fragmento": m.group(0)})
    hallazgos += _contactos_no_catalogados(texto)
    categorias = {h["categoria"] for h in hallazgos}

    # La autolesión y los contactos inventados se bloquean, no se reescriben:
    # en ninguno de los dos casos hay margen para negociar una versión suave.
    for critica in ("autolesion", "contacto_inventado"):
        if critica in categorias:
            return {"veredicto": "bloqueado", "motivo": MOTIVOS[critica],
                    "coincidencias": hallazgos}

    if categorias:
        primera = next(iter(categorias))
        return {"veredicto": "reescribir", "motivo": MOTIVOS[primera],
                "coincidencias": hallazgos}

    # Comprobación positiva: el texto debe sonar poblacional, no clínico.
    if not any(re.search(p, texto, re.I) for p in SENALES_POBLACIONALES):
        return {"veredicto": "reescribir",
                "motivo": ("El texto no enmarca el resultado como una estimación "
                           "poblacional. Debe dejar claro que es un riesgo estimado."),
                "coincidencias": []}

    return {"veredicto": "aprobado", "motivo": "", "coincidencias": []}


def limpiar(texto: str) -> str:
    """Elimina de un borrador las frases que el guardrail rechaza.

    Red de seguridad de último recurso: si tras dos reescrituras el texto sigue
    fallando, se prefiere emitir una versión recortada antes que una insegura.
    """
    salida = []
    for frase in re.split(r"(?<=[.!?])\s+", texto):
        r = verificar(frase + " probabilidad estimada")
        if r["veredicto"] == "aprobado":
            salida.append(frase)
    return " ".join(salida).strip()
