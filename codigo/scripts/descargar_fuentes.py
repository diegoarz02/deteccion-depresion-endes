"""Descarga las tipografías del proyecto y las deja autoalojadas.

Existe porque el boletín declara que funciona sin conexión —y es cierto para las
imágenes, que son SVG propios— pero cargaba las fuentes desde Google. En un aula
con mala conexión eso significa que la página cambia de aspecto a mitad de carga,
y en una sustentación es justo lo que no quieres.

Autoalojar resuelve tres cosas de una vez: elimina la dependencia externa, quita
una petición bloqueante a otro dominio, y hace verdadera la afirmación de
``CREDITOS.md``.

Solo se traen los subconjuntos **latinos**. Google sirve siete (griego, cirílico,
vietnamita…) y para un documento en español los otros seis son peso muerto.

Uso
---
    python codigo/scripts/descargar_fuentes.py
"""

from __future__ import annotations

import hashlib
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depresion import config as cfg  # noqa: E402
from depresion import diseno  # noqa: E402

DESTINOS = [cfg.RAIZ / "boletin" / "assets" / "fonts",
            cfg.RAIZ / "api" / "web" / "fonts"]

#: Google marca cada bloque con un comentario del subconjunto. Solo interesan
#: los latinos: el resto añade cientos de kilobytes que nadie va a leer.
SUBCONJUNTOS = {"latin", "latin-ext"}

AGENTE = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def _pedir(url: str) -> bytes:
    """Descarga una URL declarando un navegador moderno.

    Google devuelve WOFF2 solo si cree hablar con un navegador que lo soporta;
    con el agente por defecto de urllib sirve TrueType, que pesa el triple.
    """
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": AGENTE}), timeout=30).read()


def bloques_latinos(css: str) -> list[str]:
    """Separa el CSS en bloques @font-face y conserva los latinos."""
    partes = re.split(r"(?=/\* )", css)
    return [b for b in partes
            if (m := re.match(r"/\* (\S+) \*/", b)) and m.group(1) in SUBCONJUNTOS]


def main() -> None:
    """Descarga las fuentes y escribe el CSS que las declara en local."""
    css = _pedir(diseno.FUENTES_GOOGLE).decode("utf-8")
    bloques = bloques_latinos(css)
    print(f"CSS de Google: {len(css):,} bytes · {len(bloques)} bloques latinos")

    # Fraunces e Inter son fuentes VARIABLES: Google sirve el mismo archivo para
    # los tres pesos de una y los cuatro de la otra. Guardarlos con nombre
    # distinto multiplicaba por catorce lo que en realidad son cuatro archivos —
    # 892 kB donde bastan 254. Se deduplica por hash del contenido.
    salida, cache, total = [], {}, 0
    for bloque in bloques:
        familia = re.search(r"font-family: '([^']+)'", bloque).group(1)
        url = re.search(r"url\((https://[^)]+\.woff2)\)", bloque).group(1)
        sub = re.match(r"/\* (\S+) \*/", bloque).group(1)

        datos = _pedir(url)
        firma = hashlib.sha256(datos).hexdigest()[:12]
        if firma in cache:
            nombre = cache[firma]
        else:
            nombre = f"{familia.lower()}-{sub}-{firma}.woff2"
            cache[firma] = nombre
            total += len(datos)
            for d in DESTINOS:
                d.mkdir(parents=True, exist_ok=True)
                (d / nombre).write_bytes(datos)
            print(f"  {nombre:46s} {len(datos) / 1024:6.1f} kB")

        salida.append(bloque.replace(url, f"fonts/{nombre}").strip())

    cabecera = ("/* Tipografías autoalojadas. Generado por "
                "codigo/scripts/descargar_fuentes.py.\n"
                "   Solo subconjuntos latinos: el resto es peso muerto para un "
                "documento en español.\n"
                "   font-display: swap — el texto se lee con la fuente de respaldo "
                "mientras carga,\n"
                "   en vez de quedarse invisible. */\n\n")
    for d in DESTINOS:
        (d.parent / "fuentes.css").write_text(cabecera + "\n\n".join(salida) + "\n",
                                              encoding="utf-8")

    print(f"\nTotal: {total / 1024:.0f} kB en {len(DESTINOS)} destinos")
    for d in DESTINOS:
        print(f"  {(d.parent / 'fuentes.css').relative_to(cfg.RAIZ)}")


if __name__ == "__main__":
    main()
