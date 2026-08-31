"""Prepara los recursos gráficos del boletín: iconos e ilustraciones.

Dos fuentes, y la elección de cada una está razonada:

**Iconos: Lucide** (licencia ISC). Se descargan una sola vez a
``boletin/assets/img/iconos/`` para que el boletín funcione sin conexión y en
cualquier hosting estático. Nada de enlaces en caliente.

**Ilustraciones: originales de este proyecto.** Se descartaron dos alternativas:

- *Fotografías de personas reales* (Wikimedia, Unsplash). En salud mental, la
  foto de una persona identificable junto a la palabra "depresión" estigmatiza
  y expone. El propio protocolo del boletín lo desaconseja.
- *Bancos de ilustraciones* (unDraw, Storyset). Ninguno ofrece descarga
  programática estable: unDraw responde 404 a su CDN público y Storyset exige
  navegación manual. Enlazar en caliente rompería el boletín sin conexión.

Dibujarlas aquí resuelve las dos cosas de una vez: usan exactamente la paleta
del proyecto, no hay riesgo de licencia y transmiten acompañamiento y búsqueda
de ayuda en lugar de sufrimiento, que es el mensaje del boletín.

Uso
---
    python codigo/scripts/preparar_recursos_boletin.py
"""

from __future__ import annotations

import sys
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402

DESTINO = cfg.BOLETIN / "assets" / "img"
ICONOS = DESTINO / "iconos"
ILUSTRACIONES = DESTINO / "ilustraciones"

C = cfg.COLORES

#: Iconos de Lucide, uno por sección donde hacen falta.
ICONOS_LUCIDE = {
    "brain": "Sección 2 · qué es la depresión",
    "heart-handshake": "Sección 4 · detección temprana y apoyo",
    "users": "Sección 7 · perfil sociodemográfico",
    "map-pin": "Sección 8 · geografía",
    "activity": "Sección 9 · factores asociados",
    "trending-up": "Sección 10 · el modelo",
    "search": "Sección 11 · modelo frente a realidad",
    "phone-call": "Sección 13 · líneas de ayuda",
    "shield-check": "Encuadre ético",
    "clipboard-list": "Sección 6 · cómo lo medimos",
    "database": "Sección 5 · de dónde salen los datos",
    "message-circle-heart": "Sección 3 · la problemática",
    "triangle-alert": "Avisos y limitaciones",
    "map": "Mapas",
}

URL_LUCIDE = "https://unpkg.com/lucide-static@latest/icons/{}.svg"


def descargar_iconos() -> list[dict]:
    """Descarga los iconos de Lucide y los tiñe con el color del proyecto."""
    ICONOS.mkdir(parents=True, exist_ok=True)
    registro = []
    for nombre, uso in ICONOS_LUCIDE.items():
        destino = ICONOS / f"{nombre}.svg"
        if destino.exists():
            registro.append({"archivo": f"iconos/{nombre}.svg", "uso": uso, "estado": "ya estaba"})
            continue
        try:
            req = urllib.request.Request(
                URL_LUCIDE.format(nombre),
                headers={"User-Agent": "BoletinEpidemiologico/1.0 (academico UNMSM)"})
            with urllib.request.urlopen(req, timeout=25) as r:
                svg = r.read().decode("utf-8")
            # Lucide usa currentColor; se fija el navy para que funcione suelto.
            svg = svg.replace('stroke="currentColor"', f'stroke="{C["navy"]}"')
            destino.write_text(svg, encoding="utf-8")
            registro.append({"archivo": f"iconos/{nombre}.svg", "uso": uso, "estado": "descargado"})
        except Exception as e:
            registro.append({"archivo": f"iconos/{nombre}.svg", "uso": uso,
                             "estado": f"FALLÓ: {str(e)[:60]}"})
    return registro


# ─────────────────────────────────────────────────────────────────────
# Ilustraciones originales
# ─────────────────────────────────────────────────────────────────────


def _lienzo(cuerpo: str, ancho: int = 420, alto: int = 300) -> str:
    """Envuelve el cuerpo de un SVG en su lienzo, con los degradados comunes."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}"
     width="{ancho}" height="{alto}" role="img">
  <defs>
    <linearGradient id="cielo" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#EEF3F9"/><stop offset="100%" stop-color="#FFFFFF"/>
    </linearGradient>
    <linearGradient id="calido" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{C['dorado_claro']}"/>
      <stop offset="100%" stop-color="{C['dorado']}"/>
    </linearGradient>
  </defs>
  <rect width="{ancho}" height="{alto}" fill="url(#cielo)" rx="16"/>
{cuerpo}
</svg>"""


def _persona(x: int, y: int, escala: float, color: str, brazo: str = "") -> str:
    """Dibuja una figura humana estilizada, sin rasgos identificables."""
    return f"""  <g transform="translate({x},{y}) scale({escala})">
    <circle cx="0" cy="-46" r="17" fill="{color}"/>
    <path d="M-20 -26 Q0 -34 20 -26 L24 26 Q0 33 -24 26 Z" fill="{color}"/>
{brazo}
  </g>"""


ILUSTRACIONES_SVG = {
    "conversacion": (
        "Dos personas conversando, una escuchando a la otra",
        _lienzo(
            _persona(140, 200, 1.05, C["navy"],
                     '    <path d="M20 -14 Q52 -6 62 12" stroke="' + C["navy"] +
                     '" stroke-width="9" fill="none" stroke-linecap="round"/>')
            + _persona(290, 200, 1.05, C["navy_claro"],
                       '    <path d="M-20 -14 Q-52 -6 -62 12" stroke="' + C["navy_claro"] +
                       '" stroke-width="9" fill="none" stroke-linecap="round"/>')
            + f'  <path d="M175 128 q40 -26 80 0" stroke="{C["dorado"]}" stroke-width="4"'
              ' fill="none" stroke-linecap="round" stroke-dasharray="9 8"/>'
            + '  <circle cx="215" cy="112" r="9" fill="url(#calido)"/>'
        )),
    "apoyo": (
        "Una persona acompañando a otra, con una mano en el hombro",
        _lienzo(
            _persona(165, 205, 1.0, C["navy_claro"])
            + _persona(255, 205, 1.0, C["navy"],
                       '    <path d="M-22 -18 Q-56 -26 -74 -18" stroke="' + C["navy"] +
                       '" stroke-width="9" fill="none" stroke-linecap="round"/>')
            + '  <path d="M210 96 c-14 -18 -40 -8 -40 12 c0 20 40 40 40 40 s40 -20 40 -40'
              ' c0 -20 -26 -30 -40 -12 z" fill="url(#calido)" opacity="0.92"/>'
        )),
    "busqueda_ayuda": (
        "Una persona levantando la mano para pedir ayuda, y una puerta abierta",
        _lienzo(
            f'  <rect x="250" y="90" width="96" height="150" rx="8" fill="{C["navy"]}"'
            ' opacity="0.12"/>'
            f'  <rect x="262" y="102" width="72" height="138" rx="6" fill="url(#calido)"'
            ' opacity="0.55"/>'
            + _persona(150, 210, 1.05, C["navy"],
                       '    <path d="M18 -20 Q40 -46 44 -70" stroke="' + C["navy"] +
                       '" stroke-width="9" fill="none" stroke-linecap="round"/>')
            + f'  <path d="M206 150 h34 m-10 -10 l10 10 l-10 10" stroke="{C["dorado"]}"'
              ' stroke-width="5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
        )),
    "comunidad": (
        "Un grupo de personas de distintas edades, juntas",
        _lienzo(
            _persona(105, 215, 0.82, C["navy_claro"])
            + _persona(180, 205, 1.0, C["navy"])
            + _persona(258, 212, 0.9, C["navy_claro"])
            + _persona(325, 218, 0.74, C["navy"])
            + f'  <path d="M70 250 q140 -22 285 0" stroke="{C["dorado"]}" stroke-width="5"'
              ' fill="none" stroke-linecap="round" opacity="0.8"/>'
        )),
    "deteccion": (
        "Una lupa sobre un gráfico ascendente, la idea de detectar a tiempo",
        _lienzo(
            f'  <polyline points="80,220 140,180 190,196 250,130 320,96" fill="none"'
            f' stroke="{C["navy_claro"]}" stroke-width="7" stroke-linecap="round"'
            ' stroke-linejoin="round"/>'
            + "".join(f'  <circle cx="{x}" cy="{y}" r="7" fill="{C["navy"]}"/>'
                      for x, y in [(80, 220), (140, 180), (190, 196), (250, 130), (320, 96)])
            + f'  <circle cx="250" cy="130" r="42" fill="none" stroke="{C["dorado"]}"'
              ' stroke-width="7"/>'
            + f'  <path d="M280 160 l34 34" stroke="{C["dorado"]}" stroke-width="9"'
              ' stroke-linecap="round"/>'
        )),
    "territorio": (
        "Una silueta del territorio con marcadores de ubicación",
        _lienzo(
            f'  <path d="M170 60 q56 24 44 84 q-12 60 6 96 q18 36 -18 60 q-40 -18 -52 -66'
            f' q-12 -48 -22 -84 q-10 -36 42 -90 z" fill="{C["navy"]}" opacity="0.16"/>'
            + "".join(
                f'  <g transform="translate({x},{y})">'
                f'<path d="M0 0 c-12 -14 -20 -22 -20 -34 a20 20 0 1 1 40 0 c0 12 -8 20 -20 34 z"'
                f' fill="{col}"/><circle cx="0" cy="-34" r="7" fill="#fff"/></g>'
                for x, y, col in [(172, 132, C["dorado"]), (196, 196, C["navy"]),
                                  (152, 232, C["navy_claro"])])
        )),
}


def escribir_ilustraciones() -> list[dict]:
    """Escribe las ilustraciones SVG originales."""
    ILUSTRACIONES.mkdir(parents=True, exist_ok=True)
    registro = []
    for nombre, (descripcion, svg) in ILUSTRACIONES_SVG.items():
        destino = ILUSTRACIONES / f"{nombre}.svg"
        destino.write_text(svg, encoding="utf-8")
        registro.append({"archivo": f"ilustraciones/{nombre}.svg",
                         "descripcion": descripcion,
                         "peso_kb": round(destino.stat().st_size / 1024, 1)})
    return registro


def escribir_creditos(iconos: list[dict], ilustraciones: list[dict]) -> None:
    """Escribe el registro de procedencia de cada archivo gráfico."""
    hoy = date.today().isoformat()
    lineas = [
        "# Créditos de las imágenes del boletín",
        "",
        f"Última actualización: {hoy}",
        "",
        "Todos los archivos están **descargados o generados en local**. El boletín no enlaza",
        "ninguna imagen externa, de modo que funciona sin conexión y en cualquier hosting",
        "estático.",
        "",
        "---",
        "",
        "## Criterio editorial",
        "",
        "En salud mental, la elección de imágenes no es un asunto decorativo.",
        "",
        "- **No se usan fotografías de personas reales.** Una persona identificable junto a la",
        "  palabra «depresión» queda asociada a ella para siempre; estigmatiza y expone.",
        "- **Se evitan los clichés que estigmatizan:** la cabeza entre las manos en blanco y",
        "  negro, la silueta en el rincón oscuro, la botella junto a la persona derrumbada.",
        "  Refuerzan el estigma y envejecen mal.",
        "- **Las ilustraciones muestran acompañamiento, conversación y búsqueda de ayuda**, no",
        "  sufrimiento. El mensaje del boletín es que detectar a tiempo sirve.",
        "- Las figuras humanas son siluetas sin rasgos: no representan a nadie en concreto.",
        "",
        "---",
        "",
        "## Ilustraciones",
        "",
        "**Originales de este proyecto**, dibujadas en SVG con la paleta del boletín.",
        "",
        "Se descartaron los bancos de ilustraciones libres (unDraw, Storyset) porque ninguno",
        "ofrece descarga programática estable —el CDN público de unDraw responde 404— y",
        "enlazar en caliente rompería el boletín sin conexión. Dibujarlas aquí garantiza además",
        "que el color de acento coincide exactamente con el del resto del sitio.",
        "",
        "| Archivo | Descripción | Autor | Licencia | Peso |",
        "|---|---|---|---|---|",
    ]
    for r in ilustraciones:
        lineas.append(
            f"| `{r['archivo']}` | {r['descripcion']} | Proyecto de Epidemiología 2026-2, "
            f"UNMSM | MIT (la del repositorio) | {r['peso_kb']} KB |")

    lineas += [
        "",
        "---",
        "",
        "## Iconos",
        "",
        "**Lucide** — <https://lucide.dev> · licencia **ISC** · no exige atribución, pero se",
        f"cita igualmente. Descargados desde `unpkg.com/lucide-static` el {hoy} y teñidos con",
        "el navy del proyecto.",
        "",
        "| Archivo | Uso en el boletín | Estado |",
        "|---|---|---|",
    ]
    for r in iconos:
        lineas.append(f"| `{r['archivo']}` | {r['uso']} | {r['estado']} |")

    lineas += [
        "",
        "---",
        "",
        "## Otros recursos",
        "",
        "| Archivo | Descripción | Fuente | Licencia |",
        "|---|---|---|---|",
        "| `logo_unmsm.jpg` | Escudo de la Universidad Nacional Mayor de San Marcos | "
        "Institucional | Uso académico institucional |",
        "| `flujograma_strobe.png` | Diagrama de conformación de la muestra | "
        "Generado por este proyecto | MIT |",
        "| `dag_causal.png` | Grafo acíclico dirigido del estudio | "
        "Generado por este proyecto | MIT |",
        "| `mapa_*.png` | Cartografía | Generados por este proyecto sobre límites del "
        "INEI 2023 (geogpsperu / SuyoPomalia) | MIT; límites de uso público |",
        "",
    ]
    (DESTINO / "CREDITOS.md").write_text("\n".join(lineas), encoding="utf-8")


def main() -> None:
    """Descarga los iconos, escribe las ilustraciones y registra los créditos."""
    DESTINO.mkdir(parents=True, exist_ok=True)
    print("Descargando iconos de Lucide…")
    iconos = descargar_iconos()
    for r in iconos:
        print(f"  {r['archivo']:34s} {r['estado']}")

    print("\nEscribiendo ilustraciones originales…")
    ilus = escribir_ilustraciones()
    for r in ilus:
        print(f"  {r['archivo']:38s} {r['peso_kb']:5.1f} KB")

    # El logo y las figuras que el boletín necesita
    import shutil
    for origen, nombre in [(cfg.FIGURAS / "logo_unmsm.jpg", "logo_unmsm.jpg"),
                           (cfg.DOCS / "flujograma_strobe.png", "flujograma_strobe.png"),
                           (cfg.DOCS / "dag_causal.png", "dag_causal.png")]:
        if origen.exists():
            shutil.copy(origen, DESTINO / nombre)
            print(f"  copiado {nombre}")

    for m in sorted(cfg.MAPAS.glob("mapa_*.png")):
        shutil.copy(m, DESTINO / m.name)
    print(f"  copiados {len(list(cfg.MAPAS.glob('mapa_*.png')))} mapas")

    escribir_creditos(iconos, ilus)
    fallos = [r for r in iconos if r["estado"].startswith("FALLÓ")]
    print(f"\nCréditos escritos en {DESTINO / 'CREDITOS.md'}")
    if fallos:
        print(f"⚠ {len(fallos)} iconos no se pudieron descargar: "
              f"{[r['archivo'] for r in fallos]}")


if __name__ == "__main__":
    main()
