"""Identidad visual del proyecto: paleta, tipografía y tokens compartidos.

Un solo sitio donde vive el aspecto de todo lo que se publica —boletín, app web
y figuras—, para que las tres cosas se vean como parte del mismo trabajo y no
como tres entregas cosidas.

Las decisiones, y por qué
------------------------
**El verde-teal manda, no el azul.** El lazo verde es el símbolo internacional
de la salud mental. El azul marino institucional que traía el proyecto es
correcto y anónimo: sirve igual para un banco, una aseguradora o un ministerio.
Un tema de salud mental merece un color que signifique algo en su propio campo.

**Fondo cálido, no blanco clínico.** El blanco puro y el gris azulado son los
colores del formulario médico y del laboratorio. Un tono de papel —crema muy
desaturado— baja la temperatura emocional del documento sin restarle seriedad.
Quien lee esto puede estar buscándose a sí mismo en las cifras.

**Neutros cálidos en lugar de grises fríos.** Un gris con base azul enfría; uno
con base tierra acompaña. Es un cambio que casi nadie nota conscientemente y que
cambia por completo cómo se siente una página.

**Terracota como acento, no rojo de alarma.** En salud mental el rojo señala
emergencia, y aquí casi nunca la hay: se habla de prevalencias poblacionales, no
de una urgencia. El rojo se reserva para el bloque de crisis, que es el único
sitio donde esa lectura es la correcta.

**Serif humanista en los titulares.** Todo-sans lee corporativo y distante. Una
serif de texto en los titulares y en las cifras grandes acerca el documento a un
informe leído por personas, que es lo que es.
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────
# 1. Paleta
# ─────────────────────────────────────────────────────────────────────

#: Verde-teal: el color del lazo de la salud mental. Es la voz principal.
VERDE = {
    "900": "#12352F",   # titulares sobre fondo claro
    "800": "#1A4A42",
    "700": "#236158",   # color de marca
    "600": "#2F7D71",
    "500": "#469186",   # series de datos
    "300": "#8FBDB4",
    "200": "#BEDBD5",
    "100": "#E3F0ED",
    "050": "#F1F8F6",
}

#: Salvia: el secundario. Vegetal, tranquilo, para superficies y bordes.
SALVIA = {
    "700": "#5A6B58",
    "500": "#87977F",
    "300": "#B5C0AC",
    "100": "#E6EAE0",
}

#: Terracota: el acento cálido. Señala «mira esto», no «esto es un peligro».
ARCILLA = {
    "700": "#8F4526",
    "600": "#A85732",
    "500": "#C4714E",
    "300": "#DFA98F",
    "100": "#F7E7DF",
}

#: Miel: el segundo acento, para lo destacado y los avisos suaves.
MIEL = {
    "700": "#8A6417",
    "600": "#A87D20",
    "500": "#D2A03C",
    "300": "#E8CB8C",
    "100": "#FAF0DA",
}

#: Ciruela: reservado para el bloque de crisis. Es el único rojo del sistema, y
#: tira a vino en lugar de a bermellón: serio, no estridente.
CIRUELA = {
    "700": "#7A2438",
    "500": "#9C3A50",
    "100": "#F6E4E8",
}

#: Neutros con base tierra. Sustituyen a los grises azulados del diseño previo.
TIERRA = {
    "900": "#25211D",   # texto principal — marrón muy oscuro, no negro
    "700": "#4A443D",
    "500": "#6E675E",   # texto secundario
    "300": "#A8A197",
    "200": "#D8D2C7",   # bordes
    "100": "#EDE8DF",
    "050": "#F7F4EE",   # fondo de página — papel
    "000": "#FFFDFA",   # superficie de tarjeta — blanco cálido
}

#: Escala secuencial para mapas y coropléticos. Un solo tono, luminosidad
#: creciente: se lee bien en gris y no sugiere una frontera donde no la hay.
SECUENCIAL = ["#EAF3F0", "#C4DFD8", "#94C4B9", "#5FA396", "#357F73", "#1A5A50", "#12352F"]

#: Escala categórica. El orden importa: las dos primeras son las que más se usan
#: y son distinguibles en escala de grises y con daltonismo rojo-verde.
CATEGORICA = [
    VERDE["700"], ARCILLA["500"], MIEL["600"],
    SALVIA["700"], VERDE["300"], TIERRA["500"],
]

#: Semánticos. El verde de «protector» es el mismo de la marca a propósito: en
#: este proyecto lo protector y lo saludable son la misma idea.
PROTECTOR = VERDE["600"]
RIESGO = ARCILLA["600"]
CRISIS = CIRUELA["700"]


# ─────────────────────────────────────────────────────────────────────
# 2. Tipografía
# ─────────────────────────────────────────────────────────────────────

#: Fraunces para titulares y cifras grandes; Inter para el texto corrido.
#: Fraunces es una serif variable con eje óptico: a tamaño grande gana carácter
#: y a tamaño pequeño se mantiene legible. Ambas tienen diacríticos españoles
#: bien resueltos, que no es evidente en tipografías de pantalla.
FUENTES_GOOGLE = (
    "https://fonts.googleapis.com/css2?"
    "family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&"
    "family=Inter:wght@400;500;600;700&display=swap"
)

PILA_TITULO = ('Fraunces, "Iowan Old Style", "Palatino Linotype", Georgia, '
               '"Times New Roman", serif')
PILA_TEXTO = ('Inter, "Segoe UI", system-ui, -apple-system, "Helvetica Neue", '
              "Arial, sans-serif")


# ─────────────────────────────────────────────────────────────────────
# 3. Tokens CSS
# ─────────────────────────────────────────────────────────────────────


def _bloque(prefijo: str, escala: dict[str, str]) -> str:
    """Convierte una escala de color en declaraciones de variable CSS."""
    return "\n".join(f"  --{prefijo}-{k}: {v};" for k, v in escala.items())


def variables_css() -> str:
    """Devuelve el bloque `:root` con toda la identidad, y su versión oscura.

    El tema oscuro no invierte la paleta: recalcula cada token con la misma
    intención. Invertir la luminosidad de un verde profundo da un verde neón
    que contradice justo el tono que se buscaba.
    """
    return f"""/* ═══════════════════════════════════════════════════════════════
   Identidad visual — Depresión en el Perú (ENDES 2025)
   Generado por codigo/src/depresion/diseno.py. No editar a mano.
   ═══════════════════════════════════════════════════════════════ */

/* Las tipografías se sirven desde el propio sitio (assets/fuentes.css), no
   desde Google. Un @import a otro dominio bloquea el renderizado y hace que la
   página cambie de aspecto a mitad de carga si la conexión es mala — justo lo
   que no quieres durante una sustentación. Las descarga
   codigo/scripts/descargar_fuentes.py. */

:root {{
{_bloque("verde", VERDE)}
{_bloque("salvia", SALVIA)}
{_bloque("arcilla", ARCILLA)}
{_bloque("miel", MIEL)}
{_bloque("ciruela", CIRUELA)}
{_bloque("tierra", TIERRA)}

  /* Roles semánticos: el resto de la hoja usa estos, no los colores crudos.
     Así un cambio de paleta no obliga a tocar cada regla. */
  --marca: var(--verde-700);
  --marca-oscura: var(--verde-900);
  --marca-clara: var(--verde-100);
  --acento: var(--arcilla-500);
  --acento-oscuro: var(--arcilla-700);
  --acento-claro: var(--arcilla-100);
  --destacado: var(--miel-600);
  --destacado-claro: var(--miel-100);
  --protector: {PROTECTOR};
  --riesgo: {RIESGO};
  --crisis: var(--ciruela-700);
  --crisis-fondo: var(--ciruela-100);

  --texto: var(--tierra-900);
  --texto-suave: var(--tierra-500);
  --texto-tenue: var(--tierra-300);
  --borde: var(--tierra-200);
  --borde-suave: var(--tierra-100);
  --fondo: var(--tierra-050);
  --superficie: var(--tierra-000);
  --superficie-alt: var(--verde-050);

  --fuente-titulo: {PILA_TITULO};
  --fuente-texto: {PILA_TEXTO};

  /* Sombras con tinte del propio color de marca en vez de negro puro: una
     sombra gris sobre fondo cálido se ve sucia. */
  --sombra-1: 0 1px 2px rgba(18, 53, 47, .06);
  --sombra-2: 0 1px 3px rgba(18, 53, 47, .05), 0 8px 24px rgba(18, 53, 47, .07);
  --sombra-3: 0 2px 6px rgba(18, 53, 47, .06), 0 18px 48px rgba(18, 53, 47, .10);

  --radio-s: 8px;
  --radio: 14px;
  --radio-l: 22px;
  --ancho: 1180px;
  --ancho-texto: 68ch;
}}

[data-tema="oscuro"] {{
  --verde-900: #CFE6E0; --verde-800: #B9DBD3; --verde-700: #9BCCC1;
  --verde-600: #7FBBAE; --verde-500: #5FA396; --verde-300: #3D7268;
  --verde-200: #2A574F; --verde-100: #1B3B36; --verde-050: #16302C;
  --salvia-700: #C3CDBB; --salvia-500: #9AA792; --salvia-300: #5E6A58;
  --salvia-100: #2B322A;
  --arcilla-700: #F0C0A8; --arcilla-600: #E5AC90; --arcilla-500: #D89877;
  --arcilla-300: #A66B4C; --arcilla-100: #3A2318;
  --miel-700: #F2D79C; --miel-600: #E8C67F; --miel-500: #D2A03C;
  --miel-300: #8A6417; --miel-100: #33280F;
  --ciruela-700: #EDA9B6; --ciruela-500: #C77E8E; --ciruela-100: #38181F;
  --tierra-900: #F2EEE7; --tierra-700: #D6D0C6; --tierra-500: #A49D92;
  --tierra-300: #6E675E; --tierra-200: #3A352F; --tierra-100: #2A2621;
  --tierra-050: #16140F; --tierra-000: #201D18;

  --sombra-1: 0 1px 2px rgba(0, 0, 0, .4);
  --sombra-2: 0 1px 3px rgba(0, 0, 0, .35), 0 8px 24px rgba(0, 0, 0, .45);
  --sombra-3: 0 2px 6px rgba(0, 0, 0, .4), 0 18px 48px rgba(0, 0, 0, .5);
}}

/* Quien pide menos movimiento, recibe menos movimiento. No es un extra: para
   algunas personas la animación es un síntoma, no un adorno. */
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{
    animation-duration: .01ms !important; animation-iteration-count: 1 !important;
    transition-duration: .01ms !important; scroll-behavior: auto !important;
  }}
}}
"""


def escribir_tokens(destinos: list) -> None:
    """Escribe el archivo de tokens en cada destino indicado."""
    css = variables_css()
    for d in destinos:
        d.parent.mkdir(parents=True, exist_ok=True)
        d.write_text(css, encoding="utf-8")
