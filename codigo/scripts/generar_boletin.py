"""Fase 3 · Boletín epidemiológico de quince secciones.

Se genera desde ``resultados/``: si el análisis cambia, el boletín se rehace con
un comando. Nada se copia a mano.

Tres reglas de redacción que gobiernan este archivo:

1. **La carátula es el único sitio con datos institucionales.** El resto de
   páginas lleva una cabecera ligera. Repetir el logo y la lista de integrantes
   en trece páginas convierte un boletín en un formulario.

2. **Cada gráfico se explica, y cada explicación se abre distinto.** Si las
   catorce empiezan con «este gráfico muestra», el lector deja de leerlas a la
   tercera. Se alterna deliberadamente entre pregunta, dato que impacta,
   comparación, contradicción, analogía y consecuencia práctica.

3. **Los gráficos técnicos se explican en la propia prosa.** Nadie fuera de la
   carrera sabe leer un forest plot ni una curva de calibración, así que la
   explicación dice qué es cada elemento y qué conviene comparar, sin recuadros
   aparte que repitan lo que el texto ya cuenta.

Uso
---
    python codigo/scripts/generar_boletin.py
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import referencias_boletin as ref  # noqa: E402  (las citas y la lista salen de aquí)

from depresion import config as cfg  # noqa: E402

SALIDA = cfg.BOLETIN
IMG = "assets/img"

PAGINAS = [
    ("index.html", "Portada", None),
    ("01-que-es.html", "Qué es", "2"),
    ("02-problematica.html", "En el Perú", "3"),
    ("03-deteccion.html", "Detección", "4"),
    ("04-datos.html", "Los datos", "5"),
    ("05-medicion.html", "Cómo medimos", "6"),
    ("06-quienes.html", "Quiénes son", "7"),
    ("07-geografia.html", "Dónde", "8"),
    ("08-factores.html", "Qué se asocia", "9"),
    ("09-asociacion.html", "Fuerza e impacto", "10"),
    ("10-modelo.html", "El modelo", "11"),
    ("11-shap.html", "Modelo y realidad", "12"),
    ("12-validez.html", "Sesgos y límites", "13"),
    ("13-conclusiones.html", "Qué significa", "14"),
    ("14-cierre.html", "Ayuda y cierre", "15"),
]
TOTAL = len(PAGINAS)

REPO = "https://github.com/diegoarz02/deteccion-depresion-endes"
WEB = "https://depresion-endes.onrender.com"

# La URL de Pages de un repositorio de proyecto lleva SIEMPRE la ruta del
# repositorio: sin ella apunta al sitio de usuario, que es otra cosa. Es el
# error clásico y no se ve hasta que el enlace está publicado.
PAGES = "https://diegoarz02.github.io/deteccion-depresion-endes/"


# ─────────────────────────────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────────────────────────────


def num(valor: float, decimales: int = 2) -> str:
    """Formatea un número con la coma decimal del español.

    Las tablas y los ejes de las figuras usan punto por convención técnica del
    proyecto, pero en prosa castellana el separador es la coma. Mezclar los dos
    en el mismo párrafo se lee mal.
    """
    return f"{valor:.{decimales}f}".replace(".", ",")


def pc(valor: float, decimales: int = 1) -> str:
    """Porcentaje en prosa: ``6,98 %`` (coma decimal y espacio antes del signo)."""
    return f"{valor:.{decimales}f}".replace(".", ",") + " %"


def fp(p: float) -> str:
    """Valor p en prosa, con la convención de publicación."""
    if p < 0.001:
        return "&lt; 0,001"   # se escribe en HTML: un «<» suelto abriría una etiqueta
    return f"{p:.3f}".replace(".", ",")


def tabla(nombre: str) -> pd.DataFrame:
    """Carga una tabla de resultados por su nombre base."""
    for carpeta in (cfg.TABLAS, cfg.MAPAS):
        p = carpeta / f"{nombre}.csv"
        if p.exists():
            return pd.read_csv(p)
    raise FileNotFoundError(f"No existe la tabla {nombre}")


def html_tabla(df: pd.DataFrame, columnas: dict[str, str],
               numericas: frozenset = frozenset(), caption: str = "") -> str:
    """Convierte un DataFrame en tabla HTML accesible."""
    def celda(c, v):
        clase = ' class="num"' if c in numericas else ""
        if isinstance(v, float):
            v = (f"{v:,.2f}".replace(",", " ") if abs(v) < 1e4
                 else f"{v:,.0f}".replace(",", " "))
        return f"<td{clase}>{v}</td>"

    filas = "".join("<tr>" + "".join(celda(c, r[c]) for c in columnas) + "</tr>"
                    for _, r in df.iterrows())
    cab = "".join(
        '<th scope="col"' + (' class="num"' if c in numericas else "") + f">{t}</th>"
        for c, t in columnas.items())
    cap = f"<caption>{caption}</caption>" if caption else ""
    return (f'<div class="tabla-scroll"><table>{cap}<thead><tr>{cab}</tr></thead>'
            f"<tbody>{filas}</tbody></table></div>")


def figura(archivo: str, titulo: str, explicacion: str, ficha: str, alt: str) -> str:
    """Bloque de gráfico: título que afirma, explicación en prosa, imagen y ficha técnica.

    La explicación lleva dentro la forma de leer el gráfico: qué es cada elemento, qué
    comparar y qué se concluye. No hay un recuadro aparte con instrucciones, porque duplica
    lo que el texto ya dice y corta la lectura.
    """
    return f"""<figure class="figura">
  <p class="titulo-hallazgo">{titulo}</p>
  <p class="explicacion">{explicacion}</p>
  <div class="lienzo"><img src="{IMG}/{archivo}" alt="{alt}" loading="lazy"></div>
  <figcaption class="ficha">{ficha}</figcaption>
</figure>"""


PIE = """<footer><div class="contenedor"><div class="cols">
  <div>
    <h4>Fuente</h4>
    Encuesta Demográfica y de Salud Familiar 2025<br>
    Instituto Nacional de Estadística e Informática<br>
    Módulos CSALUD01 y RECH0 · n = 30 226
  </div>
  <div>
    <h4>Límites geográficos</h4>
    INEI 2023, vía geogpsperu / SuyoPomalia<br>
    25 departamentos · 196 provincias
  </div>
  <div>
    <h4>Reproducibilidad</h4>
    Todo el análisis se regenera con un comando.<br>
    <a href="%REPO%">Código y datos en GitHub</a>
  </div>
  <div>
    <h4>¿Necesitas ayuda?</h4>
    Línea 113, opción 5 (salud mental)<br>
    Gratuita, 24 horas, MINSA<br>
    <a href="14-cierre.html">Todos los recursos</a>
  </div>
</div>
<!-- El descargo va en el pie compartido, no solo en la primera página: quien
     entra por un enlace directo a la sección del modelo tiene que leerlo
     igual que quien empieza por el principio. -->
<p class="descargo-pie">
  <strong>Esto es un tamizaje poblacional, no un diagnóstico.</strong>
  El PHQ-9 identifica sintomatología, no enfermedad, y ninguna cifra de este boletín
  describe a una persona concreta. El modelo estadístico discrimina de forma moderada
  (AUC 0,67): sirve para comparar grupos y orientar dónde poner recursos, no para decidir
  sobre nadie. Si algo de lo que lees te resuena, hablar con un profesional de salud mental
  es el paso que sí puede evaluar tu situación.
</p>
</div></footer>
<script>
function alternarIndice() {
  var h = document.querySelector('header.nav');
  var b = document.querySelector('.boton-indice');
  var abierto = h.getAttribute('data-indice') === 'abierto';
  h.setAttribute('data-indice', abierto ? 'cerrado' : 'abierto');
  b.setAttribute('aria-expanded', String(!abierto));
}

function alternarTema() {
  const r = document.documentElement;
  const nuevo = r.getAttribute('data-tema') === 'oscuro' ? 'claro' : 'oscuro';
  r.setAttribute('data-tema', nuevo);
  localStorage.setItem('tema', nuevo);
}
(function () {
  const g = localStorage.getItem('tema');
  if (g) document.documentElement.setAttribute('data-tema', g);
  else if (window.matchMedia('(prefers-color-scheme: dark)').matches)
    document.documentElement.setAttribute('data-tema', 'oscuro');
})();
</script>""".replace("%REPO%", REPO)


#: Etiquetas de los análisis que se muestran con otra redacción en el boletín.
ETIQUETAS_VISIBLES = {
    "Exactitud del modelo trivial": "Exactitud del modelo de referencia",
    "Referencia obligada: predecir 'nadie' acierta el 93 %": "Punto de comparación: responder «nadie» acierta el 93 %",
    "Modelo trivial (predice 'nadie')": "Modelo de referencia (responde «nadie»)",
    "La última fila es la referencia obligada.": "La última fila es el punto de comparación.",
}


def plantilla(archivo: str, titulo: str, contenido: str, numero: str | None = None) -> str:
    """Arma la página y aplica las etiquetas con redacción propia del boletín."""
    html = _plantilla_base(archivo, titulo, contenido, numero)
    for antes, despues in ETIQUETAS_VISIBLES.items():
        html = html.replace(antes, despues)
    return html


def _plantilla_base(archivo: str, titulo: str, contenido: str, numero: str | None = None) -> str:
    """Envuelve el contenido en el esqueleto común, con cabecera ligera."""
    enlaces = "".join(
        f'<a href="{h}"' + (' aria-current="page"' if h == archivo else "") + f">{t}</a>"
        for h, t, _ in PAGINAS)
    idx = [p[0] for p in PAGINAS].index(archivo)
    anterior = PAGINAS[idx - 1] if idx > 0 else None
    siguiente = PAGINAS[idx + 1] if idx < len(PAGINAS) - 1 else None
    izq = f'<a href="{anterior[0]}">← {anterior[1]}</a>' if anterior else "<span></span>"
    der = f'<a href="{siguiente[0]}">{siguiente[1]} →</a>' if siguiente else "<span></span>"
    nav_pag = f'<div class="paginacion">{izq}{der}</div>'
    etiqueta_num = f'<span class="num">{numero} de {TOTAL}</span>' if numero else ""

    # Saltos rápidos en la propia barra: llevan el título como `title` para que
    # se sepa a dónde van sin ocupar el ancho de escribirlo.
    salto_anterior = (f'<a class="salto" href="{anterior[0]}" title="{anterior[1]}" '
                      f'aria-label="Anterior: {anterior[1]}">‹</a>' if anterior else "")
    salto_siguiente = (f'<a class="salto" href="{siguiente[0]}" title="{siguiente[1]}" '
                       f'aria-label="Siguiente: {siguiente[1]}">›</a>' if siguiente else "")
    progreso = round((idx + 1) / len(PAGINAS) * 100)

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo} · Depresión en el Perú (ENDES 2025)</title>
<meta name="description" content="Boletín epidemiológico sobre la depresión en la población peruana de 15 y más años, a partir de la ENDES 2025 del INEI.">
<link rel="icon" href="data:,">
<link rel="stylesheet" href="assets/fuentes.css">
<link rel="stylesheet" href="assets/css/estilo.css">
</head>
<body>
<a class="saltar" href="#contenido">Saltar al contenido</a>
<header class="nav"><div class="nav-inner">
  <a class="marca" href="index.html">Depresión en el Perú{etiqueta_num}</a>
  <div class="nav-controles">
    {salto_anterior}{salto_siguiente}
    <button class="boton-indice" onclick="alternarIndice()" aria-expanded="false"
            aria-controls="indice-secciones">Secciones</button>
    <button class="boton-tema" onclick="alternarTema()" aria-label="Cambiar entre tema claro y oscuro">◐</button>
  </div>
  <nav class="enlaces" id="indice-secciones" aria-label="Secciones del boletín">{enlaces}</nav>
</div>
<div class="progreso"><div style="width:{progreso}%"></div></div>
</header>
<main id="contenido"><div class="contenedor">
{contenido}
{nav_pag}
</div></main>
{PIE}
</body></html>"""


def cabecera(numero: str, icono: str, titulo: str) -> str:
    """Cabecera de sección con su número e icono."""
    return f"""<div class="seccion-cabecera">
  <img src="{IMG}/iconos/{icono}.svg" alt="" aria-hidden="true">
  <span class="seccion-num">Sección {numero} de {TOTAL}</span>
</div>
<h2>{titulo}</h2>"""


# ─────────────────────────────────────────────────────────────────────
# 1 · Carátula
# ─────────────────────────────────────────────────────────────────────


def pagina_caratula() -> str:
    """Única página con los datos institucionales completos."""
    prev = tabla("tabla_08_prevalencias_ponderadas")
    nac = prev[prev.variable == "Total"].iloc[0]
    brecha = tabla("tabla_11_brecha_atencion").iloc[0]

    integrantes = ["Arapa Lazo, Julio", "Araujo Villegas, Diego Alonso",
                   "Hidalgo Huachaca, Dante", "Montero Tabori, Melany",
                   "Torres, Matías", "Zegarra, William"]
    equipo = "".join(f"<span>{i}</span>" for i in integrantes)

    guia = pd.DataFrame([
        {"s": "2 – 4", "q": "Contexto",
         "d": "Qué es la depresión, cómo se manifiesta en el Perú y qué cambia cuando se detecta a tiempo"},
        {"s": "5 – 6", "q": "Método",
         "d": "De dónde salen los datos y cómo se midió cada cosa"},
        {"s": "7 – 13", "q": "Resultados",
         "d": "Quiénes son, dónde están, qué se asocia, qué tan fuerte y cuánto pesa, qué dice "
              "el modelo y en qué se contradice, y qué sesgos pueden mover las cifras"},
        {"s": "14 – 15", "q": "Cierre",
         "d": "Qué concluimos, qué no permiten concluir los datos y dónde pedir ayuda"},
    ])

    contenido = f"""<div class="caratula"><div class="contenedor">
  <img class="logo" src="{IMG}/logo_unmsm.jpg"
       alt="Escudo de la Universidad Nacional Mayor de San Marcos">
  <p class="institucion">
    <strong>Universidad Nacional Mayor de San Marcos</strong><br>
    Facultad de Ciencias Matemáticas<br>
    Escuela Profesional de Estadística<br>
    Curso de Epidemiología
  </p>
  <div class="regla"></div>
  <h1>Depresión en la población peruana de 15 y más años</h1>
  <p class="subtitulo">
    Factores conductuales, sociales, clínicos y geográficos asociados a la
    sintomatología depresiva. Un análisis de la Encuesta Demográfica y de Salud
    Familiar 2025.
  </p>
  <div class="equipo">{equipo}</div>
  <p class="pie">
    Docente: Mg. Carlos Alberto Jaimes Velásquez<br>
    Lima – Perú, 2026
  </p>
  <a class="bajar" href="01-que-es.html">Empezar a leer →</a>
</div></div>

<div class="contenedor" style="padding-top:56px">
  <section>
    <h2>El boletín en cuatro cifras</h2>
    <p class="entradilla">Los resultados se apoyan en 30 226 personas entrevistadas en todo el país
    durante la ENDES 2025. Las cifras se estiman con el diseño muestral de la encuesta, como
    corresponde cuando las personas se entrevistan por conglomerados y no una a una.</p>
    <div class="kpis">
      <div class="kpi">
        <div class="valor">{pc(nac.prevalencia, 2)}</div>
        <div class="nombre">Prevalencia nacional</div>
        <div class="detalle">PHQ-9 ≥ 10 · IC 95 % {nac.ic_95.strip("()").replace(" – ", " a ").replace(".", ",")}</div>
      </div>
      <div class="kpi atencion">
        <div class="valor">{pc(brecha.brecha)}</div>
        <div class="nombre">No recibió atención</div>
        <div class="detalle">De quienes dan positivo al tamizaje</div>
      </div>
      <div class="kpi">
        <div class="valor">1 de 14</div>
        <div class="nombre">Personas con síntomas</div>
        <div class="detalle">Moderados o graves, de 15 años o más</div>
      </div>
      <div class="kpi">
        <div class="valor">11,6</div>
        <div class="nombre">Razón de prevalencias</div>
        <div class="detalle">Puno frente a Ucayali</div>
      </div>
    </div>

    <h3>Cómo está organizado</h3>
    <p>Las cuatro primeras secciones cuentan de qué hablamos y por qué importa. Desde la quinta
    entramos en los datos, el método y los resultados, y la última reúne los recursos de ayuda,
    por si alguna parte de este recorrido te resulta cercana.</p>

    {html_tabla(guia, {"s": "Secciones", "q": "Bloque", "d": "Contenido"})}
  </section>
</div>"""

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Depresión en el Perú · Boletín epidemiológico ENDES 2025</title>
<meta name="description" content="Boletín epidemiológico sobre la depresión en la población peruana de 15 y más años, a partir de la ENDES 2025 del INEI.">
<link rel="icon" href="data:,">
<link rel="stylesheet" href="assets/fuentes.css">
<link rel="stylesheet" href="assets/css/estilo.css">
</head>
<body>
<a class="saltar" href="#contenido">Saltar al contenido</a>
<main id="contenido">{contenido}</main>
{PIE}
</body></html>"""


# ─────────────────────────────────────────────────────────────────────
# 2 · Qué es la depresión
# ─────────────────────────────────────────────────────────────────────


def pagina_que_es() -> str:
    """Divulgación: qué es la depresión y cómo se manifiesta."""
    items = tabla("tabla_10_items_phq9")
    top = items.nlargest(3, "media")

    contenido = f"""<section>
{cabecera("2", "brain", "¿Qué es la depresión?")}
<p class="entradilla">La depresión no es lo mismo que la tristeza. La tristeza va y viene, tiene un motivo y se
disuelve sola. La depresión se queda, no siempre necesita un motivo y no se disuelve por
voluntad propia.</p>

<div class="dos-columnas">
  <div>
    <p>La Organización Mundial de la Salud (OMS) la describe como un trastorno mental frecuente:
    un estado de ánimo deprimido, o una pérdida del placer o del interés por las actividades,
    que ocupa la mayor parte del día, casi todos los días, durante al menos dos semanas
    {ref.par("oms2026")}.</p>

    <p>La palabra clave es <strong>persistente</strong>. Alguien puede pasar un mal día,
    una mala semana, un duelo. Eso es parte de estar vivo. Lo que distingue a la depresión
    es que el estado se instala y empieza a interferir con dormir, comer, trabajar,
    estudiar y relacionarse.</p>

    <p>Tampoco es cuestión de carácter ni de falta de voluntad. Resulta de interacciones
    complejas entre factores sociales, psicológicos y biológicos, y hay tratamientos eficaces,
    tanto psicológicos como farmacológicos {ref.par("oms2026")}.</p>
  </div>
  <div>
    <img class="ilustracion" src="{IMG}/ilustraciones/conversacion.svg"
         alt="Ilustración de dos personas conversando, una escuchando a la otra">
    <p class="credito-img">Ilustración original del proyecto</p>
  </div>
</div>

<h3>Cómo se manifiesta</h3>
<p>El PHQ-9 recoge nueve síntomas que van del ánimo al sueño y a la energía. En los datos
de este boletín, los más frecuentes no son los que uno esperaría:</p>

{html_tabla(top[["sintoma", "pct_positivo", "pct_relevante"]],
            {"sintoma": "Síntoma", "pct_positivo": "Lo reportó al menos un día (%)",
             "pct_relevante": "La mayoría de días (%)"},
            frozenset({"pct_positivo", "pct_relevante"}),
            "Los tres síntomas más reportados en la ENDES 2025, sobre 30 401 personas.")}

<p>El sueño y la energía encabezan la lista: quien duerme mal y anda sin fuerzas está
reportando dos de los síntomas que el cuestionario cuenta, aunque no use la palabra
«depresión» para describirlo.</p>

<div class="nota atencion">
  <strong>Una aclaración antes de seguir.</strong> A lo largo de este boletín hablamos de
  «sintomatología depresiva» y no de «depresión diagnosticada». El instrumento que usa la
  encuesta es un cuestionario de tamizaje: identifica a quien probablemente necesita una
  evaluación, no reemplaza el diagnóstico de un profesional.
</div>

<h3>Cuánto pesa en el mundo</h3>
<p>La OMS estima que unos 322 millones de personas viven con depresión, y que la padece el
5,2 % de los adultos del mundo {ref.par("oms2026")}. Si se mira el conjunto de los
trastornos mentales, explicaron el 14,6 % de los años vividos con discapacidad en el planeta
en 2019 {ref.par("gbd2022")}. En el Perú, un artículo de política sanitaria recuerda que la
gran mayoría de quienes padecen estos trastornos no accede a atención {ref.par("toyama2017")},
y de eso trata la sección 3.</p>
</section>"""
    return plantilla("01-que-es.html", "Qué es la depresión", contenido, "2")


# ─────────────────────────────────────────────────────────────────────
# 3 · La problemática en el Perú
# ─────────────────────────────────────────────────────────────────────


def pagina_problematica() -> str:
    """El problema en cifras peruanas, con la brecha de atención."""
    brecha = tabla("tabla_11_brecha_atencion")
    nacional = brecha.brecha.iloc[0]
    prev = tabla("tabla_08_prevalencias_ponderadas")
    nac = prev[prev.variable == "Total"].iloc[0]

    contenido = f"""<section>
{cabecera("3", "message-circle-heart", "La problemática en el Perú")}
<p class="entradilla">El problema peruano no es solo cuántas personas tienen síntomas
depresivos. Es cuántas de ellas no llegan nunca a un profesional.</p>

<div class="kpis">
  <div class="kpi">
    <div class="valor">{pc(nac.prevalencia, 2)}</div>
    <div class="nombre">Presenta sintomatología depresiva</div>
    <div class="detalle">Moderada o grave, PHQ-9 ≥ 10</div>
  </div>
  <div class="kpi atencion">
    <div class="valor">{pc(nacional)}</div>
    <div class="nombre">De ellas, sin atención profesional</div>
    <div class="detalle">En los últimos doce meses</div>
  </div>
  <div class="kpi">
    <div class="valor">2 029</div>
    <div class="nombre">Personas con tamizaje positivo</div>
    <div class="detalle">Solo 253 recibieron tratamiento</div>
  </div>
</div>

<div class="dos-columnas invertida">
  <div>
    <img class="ilustracion" src="{IMG}/ilustraciones/busqueda_ayuda.svg"
         alt="Ilustración de una persona levantando la mano junto a una puerta abierta">
    <p class="credito-img">Ilustración original del proyecto</p>
  </div>
  <div>
    <h3>Una brecha que no distingue</h3>
    <p>De cada cien personas que dan positivo en el tamizaje, unas ochenta y ocho no
    tuvieron contacto con un profesional de salud mental en todo el año. La cifra se
    mantiene por encima del ochenta por ciento en todos los grupos que examinamos: hombres
    y mujeres, ciudad y campo, todas las edades, todos los niveles educativos.</p>

    <p>Eso nos dice que no se trata de un grupo en particular: la atención todavía llega a muy
    pocas de las personas que la necesitan.</p>
  </div>
</div>

<h3>Por qué la gente no llega</h3>
<p>La encuesta no pregunta por los motivos, así que aquí solo podemos señalar lo que otras
fuentes documentan. Ninguno de estos factores se midió en nuestros datos:</p>

<ul>
  <li><strong>Estigma y falta de inversión.</strong> La OMS cita entre las barreras a la
  atención la falta de inversión en salud mental, la falta de profesionales capacitados y el
  estigma social asociado a los trastornos mentales {ref.par("oms2026")}.</li>
  <li><strong>Pocos especialistas y mal repartidos.</strong> Los psiquiatras son pocos y se
  concentran en Lima {ref.par("calderon2012")}; y, según los mismos autores, los médicos que no son
  psiquiatras, que atienden a la mayoría, no siempre reconocen los síntomas.</li>
  <li><strong>Entornos rurales aislados.</strong> La reforma de la atención de salud mental
  en el Perú identifica los entornos rurales aislados entre sus principales desafíos
  {ref.par("toyama2017")}.</li>
</ul>

<div class="nota">
  <strong>Lo que estos datos permiten decir.</strong> El problema de la depresión en el Perú,
  medido con esta encuesta, tiene dos partes: cuántas personas tienen síntomas y cuántas llegan
  a recibir atención. Y la segunda es la más grande de las dos.
</div>
</section>"""
    return plantilla("02-problematica.html", "La problemática en el Perú", contenido, "3")


# ─────────────────────────────────────────────────────────────────────
# 4 · Detección temprana
# ─────────────────────────────────────────────────────────────────────


def pagina_deteccion() -> str:
    """Por qué el tamizaje poblacional importa."""
    contenido = f"""<section>
{cabecera("4", "heart-handshake", "Por qué importa la detección temprana")}
<p class="entradilla">Detectar a tiempo es mucho más que un tecnicismo de salud pública: es lo
que permite que alguien llegue antes a conversar con un profesional.</p>

<div class="dos-columnas">
  <div>
    <p>Detectar a tiempo significa que alguien llegue a una evaluación y, si hace falta, a un
    tratamiento. Hay tratamientos eficaces para la depresión {ref.par("oms2026")}. Esta encuesta
    no sigue a nadie en el tiempo, así que no puede medir cuánto cambia el curso de la
    enfermedad por detectarla antes. Lo que sí mide es cuántas personas dan positivo y cuántas
    de ellas nunca llegan a un profesional.</p>

    <p>Ahí entra el <strong>tamizaje</strong>: preguntar de forma sistemática, con las
    mismas preguntas, a mucha gente. No para diagnosticar, sino para saber a quién conviene
    mirar con más atención.</p>
  </div>
  <div>
    <img class="ilustracion" src="{IMG}/ilustraciones/deteccion.svg"
         alt="Ilustración de una lupa sobre una línea ascendente">
    <p class="credito-img">Ilustración original del proyecto</p>
  </div>
</div>

<h3>Qué aporta la epidemiología</h3>
<p>Una consulta clínica responde «¿qué le pasa a esta persona?». La epidemiología responde
otra cosa: «¿a cuántas les pasa, a quiénes, dónde, y qué tienen en común?».</p>

<p>Son preguntas distintas y las dos hacen falta. Sin la primera nadie se cura; sin la
segunda no se sabe dónde poner los servicios, ni cuántos hacen falta, ni a quién priorizar
cuando no alcanzan para todos.</p>

<div class="nota">
  <strong>Qué puede y qué no puede este boletín.</strong> Puede decir dónde la prevalencia
  es más alta, qué características se asocian con ella y qué tan grande es la brecha de
  atención. Tampoco puede decir qué le va a pasar a una persona en concreto ni qué causa qué, porque los
  datos vienen de una foto tomada en un momento y no de un seguimiento en el tiempo.
</div>

<h3>El instrumento: el PHQ-9</h3>
<p>Nueve preguntas sobre cómo se ha sentido la persona en las dos últimas semanas. Cada
respuesta puntúa de 0 a 3 según cuántos días apareció el síntoma, y la suma va de 0 a 27. Los
puntajes de 5, 10, 15 y 20 corresponden a depresión leve, moderada, moderadamente grave y
grave {ref.par("kroenke2001")}. A partir de 10 se considera que hay sintomatología moderada
o grave y que conviene una evaluación profesional.</p>

<p>Es breve y se validó frente a una entrevista clínica en consultas de atención primaria:
con el corte en 10 tuvo sensibilidad y especificidad de 88 % para depresión mayor
{ref.par("kroenke2001")}. Una revisión posterior con datos individuales encontró lo mismo con
entrevistas semiestructuradas, con sensibilidad de 0,88 y especificidad de 0,85
{ref.par("levis2019")}. Ese equilibrio es lo que lo hace útil a escala de país, y también lo
que marca su límite: no reemplaza a un profesional.</p>
</section>"""
    return plantilla("03-deteccion.html", "Detección temprana", contenido, "4")


# ─────────────────────────────────────────────────────────────────────
# 5 · Los datos (bisagra)
# ─────────────────────────────────────────────────────────────────────


def pagina_datos() -> str:
    """Página bisagra: de la divulgación a la evidencia."""
    ficha = tabla("tabla_06_ficha_diseno_muestral")
    flujo = tabla("tabla_04_flujograma_strobe")
    deff = tabla("tabla_51_deff_por_variable")

    contenido = f"""<section>
{cabecera("5", "database", "¿Qué nos dicen los datos?")}
<p class="entradilla">Hasta aquí hemos hablado de qué es la depresión y por qué importa. A
partir de esta página hablamos de lo que muestran los datos, y conviene explicar primero de
dónde salen.</p>

<h3>La encuesta</h3>
<p>La <strong>Encuesta Demográfica y de Salud Familiar</strong> es la encuesta de hogares
del INEI sobre dinámica demográfica y salud. Desde 2019 su trabajo de campo corre de enero a
diciembre, y pregunta por salud reproductiva, nutrición, enfermedades crónicas y, en el módulo
que usamos aquí, salud mental {ref.par("inei2026")}.</p>

<p>Usamos la ola de 2025: el cuestionario de salud, que responde una persona de 15 años a más
seleccionada en cada hogar, cruzado con el registro del hogar, que aporta la ubicación y las
variables del diseño muestral {ref.par("inei2026")}. El estudio es observacional, transversal y
de base poblacional: describe a la población en un momento, sin seguirla en el tiempo. Por eso
mide prevalencia, no incidencia. El corte es 2025, con 165 conglomerados recuperados en enero
y febrero de 2026 {ref.par("inei2026")}.</p>

<h3>Por qué no es una encuesta cualquiera</h3>
<p>La ENDES no elige a la gente al azar de una lista nacional. Divide el país en estratos,
sortea conglomerados dentro de cada estrato y visita viviendas dentro de cada conglomerado
{ref.par("inei2026")}. Eso tiene una consecuencia estadística: las personas de un mismo
conglomerado se parecen entre sí, y tratarlas como independientes daría intervalos de
confianza demasiado estrechos {ref.par("lumley2010")}.</p>

{html_tabla(ficha, {"elemento": "Elemento del diseño", "valor": "Valor"},
            caption="Ficha del diseño muestral tal como se declaró en el análisis.")}

<div class="nota">
  <strong>Qué significa el efecto de diseño.</strong> Un valor de 3,09 quiere decir que
  estas 30 226 entrevistas aportan tanta información como unas 9 774 tomadas completamente
  al azar. Es la contrapartida natural de recorrer un país entero y no un defecto de la
  encuesta, y por eso los intervalos de este boletín lo tienen en cuenta.
</div>

<p>El efecto de diseño no es igual para todo. Las características que se agrupan
geográficamente arrastran más:</p>

{html_tabla(deff.head(6)[["etiqueta", "deff", "n_efectivo"]],
            {"etiqueta": "Variable", "deff": "Efecto de diseño",
             "n_efectivo": "Muestra efectiva"},
            frozenset({"deff", "n_efectivo"}),
            "Las seis variables con mayor agrupamiento. El área de residencia, en cambio, "
            "tiene el efecto más bajo (1,30): al ser constante dentro de cada estrato, la "
            "estratificación la estima mejor que un muestreo al azar.")}

<h3>Quiénes quedaron dentro</h3>
<p>De las 33 569 personas entrevistadas, no todas pudieron entrar al análisis:</p>

{html_tabla(flujo, {"etapa": "Etapa", "n": "Personas", "excluidos": "Salen",
                    "motivo": "Motivo"},
            frozenset({"n", "excluidos"}),
            "Conformación de la muestra analítica, paso a paso.")}

{figura(
    "flujograma_strobe.png",
    "De 33 569 entrevistas a 30 226 personas analizables",
    "Nueve de cada cien entrevistas no completaron el PHQ-9: 777 personas no estaban, 899 "
    "rechazaron, 1 419 dejaron la entrevista a medias, 70 tenían una discapacidad que lo impidió "
    "y 3 salieron por otro motivo. Otras 175 no traían el factor de ponderación. El último "
    "recorte, de 1 145 personas, no es un dato perdido: son quienes nunca asistieron a la "
    "escuela y por eso no tienen nivel educativo. El análisis con casos completos las deja "
    "fuera, y la sección 13 mide qué cambia con ellas.",
    "Fuente: ENDES 2025 (INEI). Elaboración propia siguiendo la guía STROBE "
    + ref.par("elm2007") + ".",
    "Diagrama de flujo con cuatro etapas: 33 569 personas entrevistadas, 30 401 con PHQ-9 "
    "completo, 30 226 con ponderador y 29 081 con todas las covariables.")}
</section>"""
    return plantilla("04-datos.html", "Los datos", contenido, "5")


# ─────────────────────────────────────────────────────────────────────
# 6 · Cómo lo medimos
# ─────────────────────────────────────────────────────────────────────


def pagina_medicion() -> str:
    """Definición operativa de todas las variables."""
    items = tabla("tabla_10_items_phq9")

    variables = pd.DataFrame([
        {"v": "Depresión (desenlace)",
         "d": "Puntaje PHQ-9 igual o mayor a 10, sobre los nueve ítems de las dos últimas semanas",
         "c": "2 029 personas · 6,98 %"},
        {"v": "Consumo frecuente de alcohol",
         "d": "Bebió alcohol 12 o más días en los últimos 12 meses", "c": "3 171 personas"},
        {"v": "Consumo problemático de alcohol",
         "d": "Dos o más criterios de abuso: el consumo dificultó sus actividades, le causó "
              "problemas con otros y siguió bebiendo, lo consumió en situaciones de riesgo o "
              "tuvo problemas legales",
         "c": "304 personas"},
        {"v": "Tabaquismo", "d": "Fumó cigarrillos en los últimos 12 meses",
         "c": "4 504 personas"},
        {"v": "Violencia física de pareja",
         "d": "La pareja le golpeó con el cuerpo o con un objeto al menos una vez en 12 "
              "meses. Solo se pregunta a quien tuvo pareja",
         "c": "794 de 19 841 con pareja"},
        {"v": "Hipertensión",
         "d": "Un profesional de salud le diagnosticó hipertensión arterial",
         "c": "2 623 personas"},
        {"v": "Diabetes", "d": "Un profesional de salud le diagnosticó diabetes",
         "c": "1 159 personas"},
        {"v": "Obesidad",
         "d": "Índice de masa corporal igual o mayor a 30, con peso y talla medidos por el "
              "encuestador",
         "c": "8 226 personas"},
        {"v": "Altitud de residencia",
         "d": "Metros sobre el nivel del mar del conglomerado donde vive hoy, dato del propio "
              "marco muestral. No es la altitud donde vivió antes",
         "c": "De 1 a 4 500 m"},
        {"v": "Brecha de atención",
         "d": "No recibió tratamiento de un profesional por depresión o tristeza en 12 "
              "meses, calculado solo entre quienes dan positivo",
         "c": "87,6 %"},
    ])

    contenido = f"""<section>
{cabecera("6", "clipboard-list", "Cómo lo medimos")}
<p class="entradilla">Toda cifra de este boletín depende de una definición. Aquí están
todas, sin excepción, para que cualquiera pueda discutirlas.</p>

<h3>El PHQ-9, pregunta por pregunta</h3>
<p>Nueve preguntas con el mismo encabezado: «Durante las últimas dos semanas, ¿con qué
frecuencia le han molestado los siguientes problemas?». Y las mismas cuatro respuestas
posibles: ningún día (0 puntos), varios días (1), más de la mitad de los días (2), casi
todos los días (3).</p>

{html_tabla(items[["item", "sintoma", "media", "pct_positivo"]],
            {"item": "Código", "sintoma": "Pregunta", "media": "Puntaje medio",
             "pct_positivo": "Lo reportó (%)"},
            frozenset({"media", "pct_positivo"}),
            "Los nueve ítems del PHQ-9 en la ENDES 2025. La consistencia interna del "
            "conjunto es alta: alfa de Cronbach de 0,875, en línea con el 0,87 que obtuvieron "
            "otros autores con datos de la ENDES " + ref.par("villarreal2019") + ".")}

<div class="nota atencion">
  <strong>Sobre el noveno ítem.</strong> Pregunta por pensamientos de hacerse daño. Entra
  en el puntaje porque forma parte del instrumento, pero no lo analizamos ni lo destacamos
  por separado en ningún punto de este boletín. Por cuidado hacia quien lo lea, no
  presentamos un porcentaje de ideación suicida como titular: un estudio observacional no puede
  ofrecer el acompañamiento que ese dato requeriría.
</div>

<h3>El punto de corte</h3>
<p>Usamos 10, el umbral que maximiza la combinación de sensibilidad y especificidad frente a
una entrevista diagnóstica {ref.par("levis2019")}. Un metaanálisis anterior encontró
propiedades aceptables entre 8 y 11, sin diferencias sustanciales {ref.par("manea2012")}.
Como análisis de sensibilidad repetimos todo con el corte en 5, que capta también la
sintomatología leve y sube la prevalencia al 21,4 %. Las conclusiones no cambian.</p>

<p><strong>Un límite que conviene tener presente.</strong> El corte de 10 viene de estudios de
validación hechos fuera del Perú. La versión peruana pasó por una validación de expertos, que fue un
primer paso, y quedó anunciada una validación de criterio para más adelante
{ref.par("calderon2012")}. Además, su estructura y su invarianza entre grupos se comprobaron con
datos de la ENDES {ref.par("villarreal2019")}. Esa invarianza nos dice que el cuestionario mide lo
mismo en hombres y mujeres, en el campo y en la ciudad, aunque no fija un punto de corte. Hasta
donde sabemos, no existe un estudio de criterio que proponga un umbral propio para el Perú, y si ese
umbral fuera distinto, la prevalencia que reportamos también cambiaría.</p>

<h3>Las demás variables</h3>
{html_tabla(variables, {"v": "Variable", "d": "Definición operativa", "c": "En la muestra"},
            caption="Definición exacta de cada variable usada en el análisis.")}

<p>Hay tres variables de la encuesta que no entraron como predictoras (<code>QS702</code>,
<code>QS703</code> y <code>QS704A-I</code>): la pregunta sobre cuánto dificultan los síntomas la vida
diaria, la que da paso a una segunda batería PHQ-9 y esa batería, referida a doce meses. A primera
vista podrían parecer excelentes para predecir, pero la encuesta solo se las plantea a quienes ya
declararon síntomas, así que en realidad miden lo mismo que queremos estudiar. Si las incluyéramos, el
modelo acertaría casi siempre sin aportar nada nuevo, y por eso las tratamos como parte del resultado
y no como una explicación de él.</p>

<h3>Cómo entra la edad en el modelo</h3>

<p>Las pruebas habituales muestran que la edad <strong>no se relaciona con la depresión en
línea recta</strong>: la prevalencia es alta entre los más jóvenes, baja hacia los treinta y vuelve
a subir después. Si se la trata como una recta, ese doble movimiento se compensa y la edad parece
no tener ningún efecto.</p>

<p>Hay dos formas razonables de resolverlo: partirla en <strong>grupos</strong> (15-19,
20-29, y así) o dejar que una curva flexible (una <em>spline</em>) se ajuste sola a la forma
de los datos. Probamos las dos, más otras tres, y las comparamos por un criterio que premia
el ajuste y penaliza la complejidad.</p>

<div class="tabla-scroll"><table>
<caption>Comparación de formas funcionales de la edad. Menos AIC es mejor ajuste.</caption>
<thead><tr><th scope="col">Forma</th><th scope="col" class="num">AIC</th>
<th scope="col" class="num">Diferencia</th></tr></thead>
<tbody>
<tr><td>Curva flexible (spline)</td><td class="num">14 101,8</td><td class="num">—</td></tr>
<tr><td>Cúbica</td><td class="num">14 104,6</td><td class="num">2,8</td></tr>
<tr><td>Cuadrática</td><td class="num">14 136,7</td><td class="num">34,9</td></tr>
<tr><td><strong>Grupos de edad (la que usamos)</strong></td><td class="num">14 174,0</td>
<td class="num">72,2</td></tr>
<tr><td>Línea recta</td><td class="num">14 250,6</td><td class="num">148,7</td></tr>
</tbody></table></div>

<div class="nota atencion">
  <strong>La curva ajusta mejor, pero usamos los grupos. Te contamos por qué.</strong>
  Lo que decide qué forma usar no es solo cuál ajusta mejor la edad, sino si esa elección
  <em>altera el resto del modelo</em>, y no lo hace: al cambiar de una a otra, el
  coeficiente que más se mueve lo hace un <strong>4,3 %</strong>, muy por debajo del 10 %
  que se toma como señal de que una variable está confundiendo a las demás
  {ref.par("maldonado1993", "mickey1989")}.
  <br><br>
  Aclarado eso, la elección es más de comunicación que de validez. Los
  grupos de edad dan cifras que se leen solas («el grupo de 60+ frente al de 30-39»), son la
  forma en que reportan los estudios con los que nos comparamos, y una curva flexible
  necesita un gráfico para interpretarse. La curva queda documentada como comprobación, y
  cualquiera puede reproducirla con el código.
</div>

<h3>Qué pasa con quien no contestó todo</h3>
<p>El análisis principal usa solo a quienes tienen completas las variables del modelo. Eso
deja fuera a poca gente (el faltante más grande es el nivel educativo, con un 3,8 %), pero
conviene comprobar que esa exclusión no está inclinando el resultado.</p>

<p>Se repitió el modelo rellenando los huecos con <strong>imputación múltiple</strong>:
cinco versiones del conjunto de datos, cada una con un valor plausible distinto en los
huecos, y los resultados combinados. De los diecisiete coeficientes, dieciséis se mueven
menos de un 8 %. El único que cambia de forma apreciable es la diabetes, que pasa de 1,33
a 1,49 (un 10,5 %), y se acerca al resto de enfermedades crónicas en vez de alejarse.</p>

<p>Ninguna conclusión del boletín depende de esa diferencia, aunque conviene mencionarla: quien
prefiera la versión con imputación leerá una asociación algo más intensa entre diabetes y
sintomatología depresiva, no una distinta.</p>



</section>"""
    return plantilla("05-medicion.html", "Cómo lo medimos", contenido, "6")


# ─────────────────────────────────────────────────────────────────────
# 7 · Quiénes son
# ─────────────────────────────────────────────────────────────────────


def _tasas_observadas_json() -> str:
    """Devuelve el catálogo de tasas observadas listo para incrustar.

    Va dentro de la página, no como petición a la API: el boletín vive en
    GitHub Pages, que no tiene backend, y depender del servicio de Render
    metería un arranque en frío de un minuto justo cuando alguien está
    interactuando. Son 20 kB, menos que cualquiera de las figuras.
    """
    ruta = cfg.RAIZ / "api" / "datos" / "tasas_observadas.json"
    if not ruta.exists():
        print(f"  AVISO: no existe {ruta.name}; el explorador quedará vacío")
        return '{"_orden_niveles": [], "tasas": {}}'
    crudo = json.loads(ruta.read_text(encoding="utf-8"))
    # El "</" se neutraliza: dentro de un <script>, un "</script>" en los datos
    # cerraría la etiqueta antes de tiempo.
    return json.dumps(crudo, ensure_ascii=False,
                      separators=(",", ":")).replace("</", "<\\/")


def bloque_explorador() -> str:
    """Explorador de tasas observadas, funcional sin servidor.

    Es el reencuadre llevado al boletín: aquí no hay modelo ni predicción, solo
    el recuento de cuántas personas de cada grupo dieron positivo. La búsqueda
    baja por niveles hasta encontrar el grupo más específico con casos
    suficientes, y dice cuál es en lugar de un vago «parecido».
    """
    return """
<h3>Búscate en los datos</h3>

<p>Las cifras de arriba son promedios de grupos grandes. Abajo puedes cruzar varias
características a la vez y ver <strong>cuántas personas así dieron positivo</strong> entre
las 30 226 entrevistadas. No hay modelo ni predicción: es un recuento sobre la muestra,
con su intervalo de confianza.</p>

<div class="explorador">
  <div class="explorador-campos">
    <label>Sexo
      <select id="ex-sexo"><option>Mujer</option><option>Hombre</option></select>
    </label>
    <label>Grupo de edad
      <select id="ex-edad">
        <option>15-19</option><option>20-29</option><option selected>30-39</option>
        <option>40-49</option><option>50-59</option><option>60+</option>
      </select>
    </label>
    <label>Nivel educativo
      <select id="ex-edu">
        <option>Primaria o menos</option><option selected>Secundaria</option>
        <option>Superior</option>
      </select>
    </label>
    <label>Área de residencia
      <select id="ex-area"><option selected>Urbano</option><option>Rural</option></select>
    </label>
    <label>Región natural
      <select id="ex-region">
        <option selected>Costa</option><option>Sierra</option><option>Selva</option>
      </select>
    </label>
  </div>

  <div class="explorador-salida" aria-live="polite">
    <div class="explorador-cifra" id="ex-cifra">&mdash;</div>
    <p class="explorador-frase" id="ex-frase"></p>
    <div class="explorador-puntos" id="ex-puntos" role="img"
         aria-label="Cuadrícula de cien puntos"></div>
    <p class="explorador-detalle" id="ex-detalle"></p>
  </div>
</div>

<div class="explorador-comparativa">
  <p class="comparativa-titulo">Cómo se compara este grupo</p>
  <svg id="ex-barras" class="barras-comparativas" role="img"
       aria-label="Barras comparativas"></svg>
  <p class="comparativa-nota">La rayita fina sobre cada barra es el intervalo de confianza
  del 95 %: si dos rayitas se solapan, la diferencia entre esos grupos no est&aacute;
  asegurada.</p>
  <p class="explorador-interpreta" id="ex-interpreta"></p>
</div>

<details class="detalle-numerico">
  <summary>Ver el detalle</summary>
  <div id="ex-tabla"></div>
</details>

<p class="ficha">Fuente: ENDES 2025 (INEI). Prevalencias ponderadas con el dise&ntilde;o
muestral complejo. Solo se muestran combinaciones con al menos 100 personas y 20 casos
positivos; cuando la combinaci&oacute;n exacta no llega, se busca el grupo m&aacute;s
espec&iacute;fico que s&iacute; lo haga y se dice cu&aacute;l es. Funciona sin
conexi&oacute;n al servidor: los datos van dentro de esta p&aacute;gina.</p>

<script id="datos-tasas" type="application/json">%TASAS%</script>
<script>
(function () {
  var CAT = JSON.parse(document.getElementById('datos-tasas').textContent);
  var NIVELES = CAT._orden_niveles, TASAS = CAT.tasas;
  var NACIONAL = 6.98;
  var campos = { sexo: 'ex-sexo', grupo_etario: 'ex-edad', educacion_grupo: 'ex-edu',
                 area: 'ex-area', region_natural: 'ex-region' };

  function leer() {
    var v = {};
    for (var k in campos) v[k] = document.getElementById(campos[k]).value;
    return v;
  }

  /* Baja por la escalera de niveles hasta encontrar el grupo más específico que
     tenga casos suficientes. Devuelve también qué nivel se alcanzó, porque la
     interpretación necesita saber si hubo que generalizar. */
  function buscar(v) {
    for (var i = 0; i < NIVELES.length; i++) {
      var clave = NIVELES[i].map(function (c) { return v[c]; }).join('|');
      if (TASAS[clave]) return TASAS[clave];
    }
    return null;
  }

  function coma(x, d) { return x.toFixed(d).replace('.', ','); }

  /* ── Barra comparativa ───────────────────────────────────────────
     Un número solo no dice nada; el mismo número junto a tres referencias sí.
     Se dibuja en SVG a mano: cuatro barras y sus intervalos, sin librerías. */
  function dibujarBarras(v, t) {
    var otroSexo = buscar(Object.assign({}, v, {
      sexo: v.sexo === 'Mujer' ? 'Hombre' : 'Mujer' }));
    var otraRegion = buscar(Object.assign({}, v, {
      region_natural: v.region_natural === 'Sierra' ? 'Costa' : 'Sierra' }));

    var filas = [
      { etq: 'Tu grupo', t: t, destacada: true },
      { etq: 'Todo el Perú', t: { prevalencia: NACIONAL, ic_inf: 6.49, ic_sup: 7.51 } },
    ];
    if (otroSexo) {
      filas.push({ etq: (v.sexo === 'Mujer' ? 'Hombres' : 'Mujeres') + ' igual', t: otroSexo });
    }
    if (otraRegion) {
      filas.push({ etq: 'En ' + (v.region_natural === 'Sierra' ? 'la costa' : 'la sierra'),
                   t: otraRegion });
    }

    var max = Math.max.apply(null, filas.map(function (f) { return f.t.ic_sup; })) * 1.08;
    var W = 460, alto = 34, pad = 118, y = 6, svg = '';

    filas.forEach(function (f) {
      var x = function (val) { return pad + (val / max) * (W - pad - 46); };
      var color = f.destacada ? 'var(--verde-700)' : 'var(--salvia-500)';
      svg += '<text x="' + (pad - 8) + '" y="' + (y + 15) + '" text-anchor="end" '
        + 'class="bc-etq">' + f.etq + '</text>'
        + '<rect x="' + pad + '" y="' + (y + 4) + '" width="' + (x(f.t.prevalencia) - pad)
        + '" height="15" rx="3" fill="' + color + '"/>'
        // El intervalo, dibujado encima: la barra sola sugiere una precisión
        // que el dato no tiene.
        + '<line x1="' + x(f.t.ic_inf) + '" x2="' + x(f.t.ic_sup) + '" y1="' + (y + 11.5)
        + '" y2="' + (y + 11.5) + '" class="bc-ic"/>'
        + '<line x1="' + x(f.t.ic_inf) + '" x2="' + x(f.t.ic_inf) + '" y1="' + (y + 7)
        + '" y2="' + (y + 16) + '" class="bc-ic"/>'
        + '<line x1="' + x(f.t.ic_sup) + '" x2="' + x(f.t.ic_sup) + '" y1="' + (y + 7)
        + '" y2="' + (y + 16) + '" class="bc-ic"/>'
        + '<text x="' + (x(f.t.ic_sup) + 7) + '" y="' + (y + 15) + '" class="bc-val">'
        + coma(f.t.prevalencia, 1) + ' %</text>';
      y += alto;
    });

    var g = document.getElementById('ex-barras');
    g.setAttribute('viewBox', '0 0 ' + W + ' ' + y);
    g.innerHTML = svg;
    g.setAttribute('aria-label', 'Comparación: ' + filas.map(function (f) {
      return f.etq + ', ' + coma(f.t.prevalencia, 1) + ' por ciento'; }).join('; '));
    return { otroSexo: otroSexo, otraRegion: otraRegion };
  }

  /* ── Interpretación reactiva ─────────────────────────────────────
     Cinco ramas, redactadas distinto cada una. Un texto genérico que no cambia
     con el filtro convierte el interactivo en decoración. */
  function interpretar(v, t, extras) {
    var partes = [];
    var razon = t.prevalencia / NACIONAL;

    if (razon >= 1.15) {
      partes.push('Este grupo está <strong>por encima</strong> del promedio del país: '
        + coma(t.prevalencia, 1) + ' % frente al 6,98 %, es decir '
        + coma(razon, 1) + ' veces más.');
    } else if (razon <= 0.87) {
      partes.push('Este grupo está <strong>por debajo</strong> del promedio del país: '
        + coma(t.prevalencia, 1) + ' % frente al 6,98 %. Dicho al revés, en el conjunto '
        + 'del Perú la proporción es ' + coma(1 / razon, 1) + ' veces la de este grupo.');
    } else {
      partes.push('Este grupo se mueve <strong>en torno al promedio</strong> del país, '
        + 'que es del 6,98 %.');
    }

    // El nivel dice cuántas de las cinco variables definen realmente la celda.
    if (t.nivel < 5) {
      partes.push('No hay suficientes personas con esa combinación exacta en la encuesta, '
        + 'así que la cifra corresponde a un grupo algo más amplio: el mismo <strong>'
        + t.definido_por + '</strong>.');
    }

    if (t.impreciso) {
      partes.push('Con esta muestra el dato baila bastante: la cifra real podría estar en '
        + 'cualquier punto entre ' + coma(t.ic_inf, 1) + ' % y ' + coma(t.ic_sup, 1)
        + ' %. Léela como «por ahí anda», no como un número exacto.');
    }

    var o = extras.otroSexo;
    if (o) {
      var d = t.prevalencia / o.prevalencia;
      var ellas = v.sexo === 'Mujer' ? 'las mujeres' : 'los hombres';
      var ellos = v.sexo === 'Mujer' ? 'los hombres' : 'las mujeres';
      if (d >= 1.5 || d <= 0.67) {
        var mas = d >= 1.5;
        partes.push('La diferencia por sexo es de las más grandes de todo el estudio: '
          + 'en este mismo grupo, ' + ellas + ' están ' + coma(mas ? d : 1 / d, 1)
          + ' veces ' + (mas ? 'por encima' : 'por debajo') + ' que ' + ellos + '.');
      } else if (d > 0.85 && d < 1.18) {
        // En el conjunto del país la razón entre sexos es 2,6. Que aquí se
        // acerque a 1 no es un dato aburrido: es que la brecha se cierra en
        // este grupo, y eso también dice algo.
        partes.push('Curiosamente, aquí la brecha entre sexos casi desaparece: '
          + ellas + ' y ' + ellos + ' de este mismo grupo están en '
          + coma(t.prevalencia, 1) + ' % y ' + coma(o.prevalencia, 1) + ' %. '
          + 'En el conjunto del país esa diferencia es de más del doble.');
      }
    }

    document.getElementById('ex-interpreta').innerHTML = partes.join(' ');
  }

  function pintar() {
    var v = leer();
    var t = buscar(v);
    var cifra = document.getElementById('ex-cifra');
    var frase = document.getElementById('ex-frase');
    var puntos = document.getElementById('ex-puntos');
    var detalle = document.getElementById('ex-detalle');
    var tabla = document.getElementById('ex-tabla');

    if (!t) {
      cifra.innerHTML = '&mdash;';
      frase.textContent = 'No hay suficientes personas con esta combinación en la encuesta '
        + 'para dar una cifra que se sostenga.';
      puntos.innerHTML = '';
      detalle.textContent = '';
      document.getElementById('ex-interpreta').textContent = '';
      document.getElementById('ex-barras').innerHTML = '';
      if (tabla) tabla.innerHTML = '';
      return;
    }

    cifra.innerHTML = coma(t.prevalencia, 1) + '<small> de cada 100</small>';
    frase.innerHTML = 'Entre las personas del mismo <strong>' + t.definido_por
      + '</strong>, esa proporción dio positivo al tamizaje.';

    var enteros = Math.floor(t.prevalencia), html = '';
    for (var i = 0; i < 100; i++) {
      html += i < enteros ? '<i class="on"></i>'
        : (i === enteros && t.prevalencia - enteros >= 0.25) ? '<i class="mid"></i>' : '<i></i>';
    }
    puntos.innerHTML = html;
    puntos.setAttribute('aria-label', 'Cuadrícula de cien puntos: '
      + Math.round(t.prevalencia) + ' coloreados representan a quienes dieron positivo al '
      + 'tamizaje, y ' + (100 - Math.round(t.prevalencia)) + ' en gris a quienes no.');

    detalle.innerHTML = 'Sobre ' + t.n.toLocaleString('es-PE').replace(/,/g, ' ') + ' personas, '
      + t.eventos + ' dieron positivo.';

    var extras = dibujarBarras(v, t);
    interpretar(v, t, extras);

    if (tabla) {
      tabla.innerHTML = '<table><tbody>'
        + '<tr><th>Personas del grupo</th><td>' + t.n.toLocaleString('es-PE').replace(/,/g, ' ') + '</td></tr>'
        + '<tr><th>Dieron positivo</th><td>' + t.eventos + '</td></tr>'
        + '<tr><th>Prevalencia ponderada</th><td>' + coma(t.prevalencia, 2) + ' %</td></tr>'
        + '<tr><th>Intervalo de confianza 95 %</th><td>' + coma(t.ic_inf, 2) + ' % a '
        + coma(t.ic_sup, 2) + ' %</td></tr>'
        + '<tr><th>Coeficiente de variación</th><td>' + coma(t.cv, 3)
        + (t.impreciso ? ' <span class="marca-imprecisa">imprecisa</span>' : '') + '</td></tr>'
        + '<tr><th>Variables que definen el grupo</th><td>' + t.definido_por + '</td></tr>'
        + '</tbody></table>';
    }
  }

  for (var k in campos) {
    document.getElementById(campos[k]).addEventListener('change', pintar);
  }
  pintar();
})();

</script>
""".replace("%TASAS%", _tasas_observadas_json())


def pagina_quienes() -> str:
    """Perfil sociodemográfico y prevalencias por subgrupo."""
    prev = tabla("tabla_08_prevalencias_ponderadas")

    contenido = f"""<section>
{cabecera("7", "users", "Quiénes son")}
<p class="entradilla">La depresión no se reparte de forma pareja. Se concentra en unos
grupos más que en otros, y el patrón dice bastante sobre el país. Son cifras de 2025, una especie
de fotografía: nadie fue seguido en el tiempo.</p>

{figura(
    "fig_02_prevalencia_subgrupos.png",
    "En las mujeres la prevalencia es 2,6 veces la de los hombres",
    "9,87 % frente a 3,86 %: una razón de prevalencias de 2,6. Es la brecha más grande de "
    "todo el boletín, mayor que la que separa a la sierra de la selva o a quien terminó la "
    "primaria de quien terminó la universidad. Aparece en todos los grupos de edad y tanto "
    "en el área urbana como en la rural, así que no parece deberse a ninguna de esas otras "
    "diferencias.",
    "Fuente: ENDES 2025 (INEI). Prevalencias ponderadas con el diseño muestral complejo. "
    "Las barras horizontales son intervalos de confianza al 95 %. n = 30 226.",
    "Gráfico de barras horizontales con la prevalencia de depresión por sexo, grupo etario, "
    "nivel educativo, área de residencia y región natural. La barra más larga corresponde a "
    "las mujeres, con casi 10 %, y la más corta a los hombres, con menos de 4 %.")}

{figura(
    "fig_01_distribucion_phq9.png",
    "La mitad de las personas responde cero en las nueve preguntas",
    "Ese pico en el extremo izquierdo es real: más de quince mil personas no "
    "reportaron ningún síntoma en dos semanas. La otra mitad se reparte en una cola que se "
    "adelgaza rápido. Esta forma, con muchísimos ceros y unos pocos valores altos, es la razón "
    "por la que más adelante usamos regresión logística y no una regresión lineal "
    "corriente.",
    "Fuente: ENDES 2025 (INEI). Puntaje PHQ-9 de 0 a 27 sobre 30 401 personas con las nueve "
    "preguntas respondidas. Las líneas verticales marcan los puntos de corte.",
    "Histograma del puntaje PHQ-9. Una barra muy alta en el valor cero concentra la mitad "
    "de la muestra, y el resto desciende formando una cola larga hacia la derecha.")}

<h3>La edad dibuja una U</h3>
<p>Si se mira la prevalencia por edad, el patrón no es el que suele imaginarse. No crece de
forma constante con los años: baja hasta los treinta y vuelve a subir.</p>

{html_tabla(prev[prev.variable == "Grupo etario"][["categoria", "n", "prevalencia", "ic_95"]],
            {"categoria": "Grupo etario", "n": "Personas", "prevalencia": "Prevalencia (%)",
             "ic_95": "IC 95 %"},
            frozenset({"n", "prevalencia"}),
            "Prevalencia ponderada por grupo etario.")}

<p>Los dos extremos de la vida adulta son los más afectados: la adolescencia tardía, con
8,37 %, y las personas de 60 años o más, con 9,80 %. En medio, entre los 30 y los 39, la
prevalencia cae hasta el 4,25 %, menos de la mitad.</p>

<h3>El gradiente educativo</h3>
<p>A menos años de estudio, más sintomatología: 8,77 % entre quienes llegaron como mucho a
primaria, 7,05 % en secundaria y 5,28 % en educación superior. La diferencia se mantiene en el
modelo ajustado por edad, sexo y el resto de variables (primaria o menos frente a superior: odds
ratio 1,48; IC 95 % 1,14 a 1,93), así que no es solo que las personas mayores hayan estudiado
menos. Queda fuera de estas cifras una cuarta categoría: quienes nunca asistieron a la escuela,
que la sección 13 trata aparte.</p>

{figura(
    "fig_03_items_phq9.png",
    "Dormir mal y sentirse decaído son los síntomas que más aparecen",
    "Cada barra reparte a la población entre quienes no sintieron nada, quienes lo "
    "sintieron algunos días y quienes lo sintieron casi a diario. Los problemas de sueño "
    "encabezan la lista, por delante del ánimo deprimido. Esto tiene una consecuencia práctica: "
    "una consulta por insomnio puede estar relacionada con síntomas depresivos sin que la "
    "persona lo sepa.",
    "Fuente: ENDES 2025 (INEI), n = 30 401. El ítem marcado con asterisco es el de "
    "pensamientos de hacerse daño, que se reporta pero no se analiza por separado.",
    "Gráfico de barras apiladas horizontales con los nueve síntomas del PHQ-9. Cada barra "
    "se divide en cuatro segmentos según la frecuencia del síntoma.")}
</section>"""
    return plantilla("06-quienes.html", "Quiénes son",
                     contenido + bloque_explorador(), "7")


# ─────────────────────────────────────────────────────────────────────
# 8 · Geografía
# ─────────────────────────────────────────────────────────────────────



def _contexto_departamental_json() -> str:
    """Datos de los 25 departamentos, para incrustar en la sección de geografía."""
    ruta = cfg.RAIZ / "api" / "datos" / "contexto.json"
    if not ruta.exists():
        print(f"  AVISO: no existe {ruta.name}; el selector quedará vacío")
        return '{"departamentos": [], "nacional": {}}'
    crudo = json.loads(ruta.read_text(encoding="utf-8"))
    return json.dumps(crudo, ensure_ascii=False,
                      separators=(",", ":")).replace("</", "<\\/")


def bloque_departamentos() -> str:
    """Selector que compara un departamento con el país y con sus vecinos.

    La sección de geografía tenía mapas estáticos y nada que tocar, siendo la
    que más lo pedía: un mapa invita a buscarse en él. Con los 25 departamentos
    ya calculados, el selector no cuesta ningún dato nuevo.
    """
    return """
<h3>Busca tu departamento</h3>

<p>Los mapas de arriba muestran el patrón completo. Si lo que quieres es
<strong>tu</strong> departamento, elígelo aquí y verás su cifra con su margen de error,
junto a la del país y la de los departamentos que tiene más cerca en la escala. Es una cifra de
grupo: la altitud media del departamento no se separa de la ruralidad ni del acceso a servicios,
y por eso no debe leerse como un factor aislado.</p>

<div class="selector-dep">
  <label for="dep-sel">Departamento
    <select id="dep-sel"></select>
  </label>
  <div class="dep-tarjeta" aria-live="polite">
    <div class="dep-cifra" id="dep-cifra">&mdash;</div>
    <p class="dep-nombre" id="dep-nombre"></p>
    <p class="dep-detalle" id="dep-detalle"></p>
  </div>
</div>

<svg id="dep-barras" class="barras-comparativas" role="img"
     aria-label="Comparación del departamento con el país"></svg>
<p class="explorador-interpreta" id="dep-interpreta"></p>

<details class="detalle-numerico">
  <summary>Ver el detalle</summary>
  <div id="dep-tabla"></div>
</details>

<script id="datos-departamentos" type="application/json">%DEPS%</script>
<script>
(function () {
  var D = JSON.parse(document.getElementById('datos-departamentos').textContent);
  var DEPS = D.departamentos.slice().sort(function (a, b) {
    return a.nombre.localeCompare(b.nombre, 'es'); });
  var NAC = D.nacional;
  var sel = document.getElementById('dep-sel');

  DEPS.forEach(function (d) {
    var o = document.createElement('option');
    o.value = d.codigo; o.textContent = d.nombre;
    if (d.nombre === 'Puno') o.selected = true;
    sel.appendChild(o);
  });

  /* Ucayali no tiene brecha calculada: sus casos positivos no llegan al mínimo
     para estimarla. Devolver un guion es más honesto que un cero, que se leería
     como «aquí todo el mundo recibe atención». */
  function coma(x, n) {
    return (x === null || x === undefined) ? '—' : x.toFixed(n).replace('.', ',');
  }

  /* Los dos departamentos con la prevalencia más parecida, uno por encima y
     otro por debajo. Comparar con «el vecino en la escala» sitúa mejor que
     comparar con el máximo y el mínimo, que siempre son los mismos. */
  function vecinos(d) {
    var orden = DEPS.slice().sort(function (a, b) {
      return a.prevalencia - b.prevalencia; });
    var i = orden.findIndex(function (x) { return x.codigo === d.codigo; });
    return [orden[i - 1], orden[i + 1]].filter(Boolean);
  }

  function barras(d, vs) {
    var filas = [{ etq: d.nombre, d: d, destacada: true },
                 { etq: 'Todo el Perú', d: NAC }];
    vs.forEach(function (v) { filas.push({ etq: v.nombre, d: v }); });

    var max = Math.max.apply(null, filas.map(function (f) { return f.d.ic_sup; })) * 1.08;
    var W = 460, alto = 34, pad = 122, y = 6, svg = '';
    filas.forEach(function (f) {
      var x = function (val) { return pad + (val / max) * (W - pad - 46); };
      var color = f.destacada ? 'var(--verde-700)' : 'var(--salvia-500)';
      svg += '<text x="' + (pad - 8) + '" y="' + (y + 15) + '" text-anchor="end" '
        + 'class="bc-etq">' + f.etq + '</text>'
        + '<rect x="' + pad + '" y="' + (y + 4) + '" width="' + (x(f.d.prevalencia) - pad)
        + '" height="15" rx="3" fill="' + color + '"/>'
        + '<line x1="' + x(f.d.ic_inf) + '" x2="' + x(f.d.ic_sup) + '" y1="' + (y + 11.5)
        + '" y2="' + (y + 11.5) + '" class="bc-ic"/>'
        + '<line x1="' + x(f.d.ic_inf) + '" x2="' + x(f.d.ic_inf) + '" y1="' + (y + 7)
        + '" y2="' + (y + 16) + '" class="bc-ic"/>'
        + '<line x1="' + x(f.d.ic_sup) + '" x2="' + x(f.d.ic_sup) + '" y1="' + (y + 7)
        + '" y2="' + (y + 16) + '" class="bc-ic"/>'
        + '<text x="' + (x(f.d.ic_sup) + 7) + '" y="' + (y + 15) + '" class="bc-val">'
        + coma(f.d.prevalencia, 1) + ' %</text>';
      y += alto;
    });
    var g = document.getElementById('dep-barras');
    g.setAttribute('viewBox', '0 0 ' + W + ' ' + y);
    g.innerHTML = svg;
  }

  function pintar() {
    var d = DEPS.find(function (x) { return x.codigo === sel.value; });
    if (!d) return;
    var vs = vecinos(d);
    var amplitud = d.ic_sup - d.ic_inf;
    // El coeficiente de variación no viene en este archivo; se aproxima por la
    // amplitud relativa del intervalo, que es lo que se quiere comunicar.
    var impreciso = amplitud / d.prevalencia > 0.8;

    document.getElementById('dep-cifra').innerHTML = coma(d.prevalencia, 1)
      + '<small> de cada 100</small>';
    document.getElementById('dep-nombre').textContent = d.nombre;
    document.getElementById('dep-detalle').innerHTML =
      'Sobre ' + d.n.toLocaleString('es-PE').replace(/,/g, ' ') + ' personas entrevistadas. '
      + 'Intervalo de confianza del 95 %: ' + coma(d.ic_inf, 1) + ' % a '
      + coma(d.ic_sup, 1) + ' %.'
      + (impreciso ? ' <strong>El intervalo es ancho:</strong> con esta muestra la cifra '
        + 'puntual no se sostiene sola.' : '');

    barras(d, vs);

    var partes = [];
    var r = d.prevalencia / NAC.prevalencia;
    if (r >= 1.15) {
      partes.push('<strong>' + d.nombre + '</strong> está por encima del promedio del país: '
        + 'razón de prevalencias de ' + coma(r, 2) + ' frente al total nacional.');
    } else if (r <= 0.87) {
      partes.push('<strong>' + d.nombre + '</strong> está por debajo del promedio del país: '
        + 'razón de prevalencias de ' + coma(r, 2) + ' frente al total nacional.');
    } else {
      partes.push('<strong>' + d.nombre + '</strong> se mueve en torno al promedio del país.');
    }

    if (vs.length === 2) {
      partes.push('En la escala nacional queda entre ' + vs[0].nombre + ' ('
        + coma(vs[0].prevalencia, 1) + ' %) y ' + vs[1].nombre + ' ('
        + coma(vs[1].prevalencia, 1) + ' %).');
    }

    // Si los intervalos se solapan, la diferencia entre departamentos no está
    // asegurada. Decirlo evita el titular fácil de «X duplica a Y».
    if (d.ic_inf < NAC.ic_sup && NAC.ic_inf < d.ic_sup) {
      partes.push('Su intervalo se solapa con el nacional, así que la diferencia con el '
        + 'promedio del país no está asegurada.');
    }

    if (d.brecha != null) {
      partes.push('De quienes dieron positivo aquí, el ' + coma(d.brecha, 0)
        + ' % no recibió atención profesional en todo el año.');
    }
    partes.push('La cifra describe al departamento, no a cada persona que vive en él.');
    document.getElementById('dep-interpreta').innerHTML = partes.join(' ');

    document.getElementById('dep-tabla').innerHTML = '<table><tbody>'
      + '<tr><th>Personas entrevistadas</th><td>' + d.n.toLocaleString('es-PE').replace(/,/g, ' ') + '</td></tr>'
      + '<tr><th>Prevalencia ponderada</th><td>' + coma(d.prevalencia, 2) + ' %</td></tr>'
      + '<tr><th>Intervalo de confianza 95 %</th><td>' + coma(d.ic_inf, 2) + ' % a '
      + coma(d.ic_sup, 2) + ' %</td></tr>'
      + '<tr><th>Amplitud del intervalo</th><td>' + coma(amplitud, 2)
      + ' puntos porcentuales</td></tr>'
      + '<tr><th>Brecha de atención</th><td>'
      + (d.brecha == null ? 'sin casos suficientes para estimarla'
         : coma(d.brecha, 1) + ' %') + '</td></tr>'
      + '<tr><th>Altitud media del departamento (dato de grupo)</th><td>' + d.altitud_media.toLocaleString('es-PE').replace(/,/g, ' ')
      + ' m</td></tr></tbody></table>';
  }

  sel.addEventListener('change', pintar);
  pintar();
})();
</script>
""".replace("%DEPS%", _contexto_departamental_json())

def pagina_geografia() -> str:
    """Los mapas y el análisis de altitud."""
    dep = tabla("tabla_48_prevalencia_departamental_geo").sort_values(
        "prevalencia", ascending=False)
    prov = tabla("tabla_49_prevalencia_provincial")
    alt = tabla("tabla_33_prevalencia_por_altitud")
    pasos = tabla("tabla_60_altitud_cruda_vs_ajustada").set_index("modelo")
    eco = tabla("tabla_62_ecologico_vs_individual")
    quien = tabla("tabla_67_quien_vive_en_altura").set_index("tramo_altitud")

    estimables = int(prov.estimable.sum())

    def or_ic(clave: str) -> str:
        f = pasos.loc[clave]
        return f"{num(f.or_por_1000m)} (IC 95 % {num(f.ic_inf)} a {num(f.ic_sup)})"

    c1, c2, c3, c4, c5, c6 = (next(i for i in pasos.index if i.startswith(f"({n})") and "*" not in i)
                              for n in range(1, 7))
    s1, s4, s6 = (next(i for i in pasos.index if i.startswith(f"({n}*)")) for n in (1, 4, 6))
    tabla_pasos = pd.DataFrame({
        "modelo": [i.replace("(5) + región natural (derivada de la altitud)",
                             "(5) + región natural (se deriva de la altitud)") for i in pasos.index],
        "n": [f"{int(n):,}".replace(",", " ") for n in pasos.n],
        "or": [f"{num(f.or_por_1000m)} ({num(f.ic_inf)} a {num(f.ic_sup)})"
               for _, f in pasos.iterrows()],
        "p": [fp(p) for p in pasos.p],
    })
    ecol_r = eco.iloc[0]
    ecol_pend = eco.iloc[1]
    q_bajo, q_alto = quien.loc["Menos de 1 500 m"], quien.loc["2 500 m o más"]

    contenido = f"""<section>
{cabecera("8", "map-pin", "Dónde está la depresión")}
<p class="entradilla">La razón de prevalencias entre Puno y Ucayali es de 11,6. No es un
matiz regional: es otro país dentro del mismo país. Son cifras de departamentos, es decir, de
grupos.</p>

{figura(
    "mapa_01_departamental.png",
    "La sierra sur concentra la sintomatología depresiva",
    "Puno encabeza con 12,8 %, seguido de Huancavelica con 10,6 %. En el otro extremo, "
    "Ucayali marca 1,1 % y Amazonas 3,5 %. El mapa de la derecha es igual de importante: "
    "muestra dónde la estimación es menos precisa. Los departamentos amazónicos tienen "
    "intervalos más anchos porque su muestra es más pequeña, y conviene tenerlo presente "
    "antes de sacar conclusiones sobre ellos.",
    "Fuente: ENDES 2025 (INEI); límites administrativos del INEI 2023 vía geogpsperu. "
    "Prevalencias ponderadas con el diseño complejo.",
    "Dos mapas del Perú por departamento. En el izquierdo, los tonos más oscuros de "
    "prevalencia se concentran en la sierra sur. En el derecho, los departamentos "
    "amazónicos aparecen con intervalos de confianza más anchos.")}

{html_tabla(dep.head(8)[["departamento", "n", "prevalencia", "ic_inf", "ic_sup"]],
            {"departamento": "Departamento", "n": "Personas",
             "prevalencia": "Prevalencia (%)", "ic_inf": "IC inferior",
             "ic_sup": "IC superior"},
            frozenset({"n", "prevalencia", "ic_inf", "ic_sup"}),
            "Los ocho departamentos con mayor prevalencia estimada.")}

{bloque_departamentos()}

<h3>Hasta dónde se puede bajar</h3>
{figura(
    "mapa_02_provincial.png",
    f"Solo {estimables} de las 196 provincias tienen muestra suficiente para estimar",
    "Bajar de departamento a provincia puede resultar tentador, aunque rara vez conviene. La "
    "encuesta está diseñada para dar cifras departamentales; al repartirla en 196 provincias, más "
    "de la cuarta parte queda con menos de cincuenta personas. Esas provincias van tramadas y no "
    "coloreadas, porque un mapa da a cada polígono el mismo peso visual, y pintar una provincia "
    "estimada con doce casos junto a Lima con cuatro mil daría una impresión de precisión mayor "
    "que la que permiten los datos, aunque ninguna cifra esté mal calculada.",
    f"Fuente: ENDES 2025 (INEI). Umbral mínimo de 50 personas por provincia. {estimables} "
    f"provincias estimables; la mediana de las que no alcanzan el umbral tiene 28 personas.",
    "Mapa del Perú por provincias. Las provincias con muestra suficiente aparecen "
    "coloreadas según su prevalencia; las demás llevan una trama diagonal gris que las "
    "distingue del extremo bajo de la escala de color.")}

{figura(
    "mapa_03_conglomerados.png",
    "Así se reparte la muestra por el territorio",
    "Cada punto es un conglomerado: un grupo de viviendas visitadas juntas. Son 3 143, "
    "distribuidos por todo el país. El color es la prevalencia del grupo y el tamaño, "
    "cuántas personas lo componen. Nunca se dibuja un caso individual: un punto que "
    "representara a una sola persona sería identificable al cruzarlo con otras fuentes.",
    "Fuente: ENDES 2025 (INEI). Coordenadas del centro poblado, con 1 266 registros "
    "corregidos por traer la latitud y la longitud intercambiadas en el archivo original.",
    "Mapa de puntos del Perú con 3 143 conglomerados muestrales distribuidos por todo el "
    "territorio, más densos en la costa y la sierra que en la Amazonía.")}

<h3>Dónde falta la atención</h3>
<p>Hasta aquí los mapas muestran cuánta sintomatología hay. Falta decir dónde llega la atención, que
es la otra mitad del problema.</p>

{figura(
    "mapa_05_brecha_atencion.png",
    "En Cusco, 96 de cada 100 personas con tamizaje positivo no recibieron atención",
    "Este es el mapa que debería ordenar las prioridades. Todo el país está por encima del "
    "80 %, pero los departamentos donde la brecha es mayor son, en buena medida, los mismos "
    "donde la prevalencia es más alta. La sierra sur acumula las dos cosas: más casos y "
    "menos atención.",
    "Fuente: ENDES 2025 (INEI). Calculado solo entre quienes dan positivo al tamizaje. Los "
    "departamentos con menos de 30 casos positivos no se estiman.",
    "Mapa del Perú por departamento con la brecha de atención en salud mental. Casi todo el "
    "territorio aparece en tonos oscuros, por encima del 80 %.")}

<h3>La altura, con cuidado</h3>
<p>El contraste entre Puno y Ucayali, altiplano contra selva baja, sugiere una pregunta que
otros ya se hicieron: ¿tiene algo que ver la altitud? Hay un antecedente peruano directo con la
ENDES de 2019 {ref.par("zegarra2022")}. Un metaanálisis de ocho estudios de cuatro países
estimó una prevalencia combinada de síntomas depresivos de 17,9 % entre residentes de zonas
altas, con una heterogeneidad muy alta {ref.par("basualdo2022")}, y un seguimiento de
estudiantes de medicina durante su primer año de residencia asoció vivir por encima de 900 m
con un puntaje PHQ-9 más alto {ref.par("kious2019")}.</p>

<p>Aquí la altitud cumple dos papeles a la vez. Es la <strong>exposición de interés</strong>, y es
también un <strong>posible confusor</strong> de las demás asociaciones, porque no viaja sola. En
nuestra muestra, entre quienes viven a 2 500 m o más, el {pc(q_alto.area_rural_pct)} reside en
el área rural, frente al {pc(q_bajo.area_rural_pct)} de quienes viven por debajo de 1 500 m; el
{pc(q_alto.primaria_o_menos_pct)} llegó como mucho a primaria, frente al
{pc(q_bajo.primaria_o_menos_pct)}; y el {pc(q_alto.sin_educacion_pct)} nunca asistió a la
escuela, frente al {pc(q_bajo.sin_educacion_pct)}. Y al revés: su relación con la depresión puede
estar confundida por esas mismas diferencias, por la región y por el acceso a servicios, que en
las zonas altas del Perú es menor {ref.par("zegarra2022")}. Por eso se mira de las dos maneras:
primero, si la altitud altera lo que se asocia con la depresión en los demás factores (sección
13), y ahora, qué le pasa a su propio gradiente cuando se ajusta.</p>

{figura(
    "fig_15_altitud.png",
    "Por encima de los 2 000 metros la prevalencia empieza a subir, y no antes",
    "La relación entre altitud y prevalencia existe, pero no es una recta. En el panel de la "
    "izquierda se ve que la mayoría de la muestra vive cerca del nivel del mar, de modo que ahí "
    "las estimaciones son más firmes. En el del centro, las barras agrupan por pisos y sus "
    "rayitas son el margen de error, que se ensancha donde hay poca gente: la puna es la más "
    "ancha de todas. La yunga, entre 500 y 2 000 metros, tiene incluso menos prevalencia que "
    "la costa; el ascenso arranca en la quechua y se acentúa hasta el 11,7 % de la puna. El "
    "panel de la derecha no agrupa nada, porque cada punto es un tramo de 250 metros, y "
    "permite comprobar que la curva sube con altibajos y no de forma continua. Un modelo que "
    "asumiera una línea recta se habría perdido esa forma: el ajuste con curvatura le gana por "
    "15,6 puntos de AIC.",
    "Fuente: ENDES 2025 (INEI). Altitud del conglomerado según el marco muestral, de 1 a "
    "4 500 m. Los nombres de los pisos vienen de la geografía peruana tradicional; los cortes "
    "son redondeados y propios de este análisis.",
    "Tres paneles: un histograma de la altitud de la muestra, barras de prevalencia por "
    "piso altitudinal que crecen desde la costa hasta la puna, y una nube de puntos por "
    "tramos de 250 metros con una curva de tendencia ascendente.")}

{html_tabla(alt[["altitud_categoria", "n", "prevalencia", "ic_inf", "ic_sup"]],
            {"altitud_categoria": "Piso altitudinal", "n": "Personas",
             "prevalencia": "Prevalencia (%)", "ic_inf": "IC inferior",
             "ic_sup": "IC superior"},
            frozenset({"n", "prevalencia", "ic_inf", "ic_sup"}),
            "Prevalencia ponderada por piso altitudinal. La Puna lleva asterisco: su "
            "coeficiente de variación es 0,222, por encima del 0,20 que se toma como "
            "límite para publicar una cifra puntual sin advertencia.")}

<div class="nota">
  <strong>Sobre la Puna (4 000 m o más).</strong> Es la prevalencia más alta del país,
  11,7 %, y también la menos firme: son 748 personas, el efecto de diseño es 4,88 y el
  intervalo de confianza va del 7,4 % al 18,0 %. Se muestra por completitud, no como una
  cifra puntual: lo que dice es «probablemente alto», no «11,7».
  <br><br>
  El gradiente no depende de ella. Suni, con 6 538 personas y un coeficiente de variación
  de 0,062, ya marca 8,90 % frente al 6,67 % de la costa. Si se quitara la Puna del
  análisis, la conclusión sería la misma.
</div>

<h3>La relación no es una línea recta: tiene forma de J</h3>

<p>Lo que más sorprende de estos datos no es que la prevalencia suba con la altura, sino
que <strong>primero baje</strong>. El tramo intermedio es el más bajo de los dos cortes
que se probaron: 5,96 % en la yunga (500-1 999 m) y 5,48 % en el corte de 1 500-2 499 m,
por debajo del 6,67 % de la costa. Después sube con claridad: 8,90 % en la suni y 8,76 %
por encima de los 2 500 metros.</p>

<p>Se comparó la forma de la relación ajustando tres modelos (lineal, cuadrático y con
splines) y contrastándolos por AIC. El lineal queda <strong>15,6 puntos por detrás</strong>
del mejor. Es una diferencia grande: ajustar una recta a estos datos promedia el descenso
del tramo intermedio con el ascenso del alto, y puede acabar concluyendo que la altitud
«no importa». La forma es el hallazgo, no un tecnicismo.</p>

<div class="nota atencion">
  <strong>Una diferencia con el estudio de 2019 que vale la pena explicar.</strong> En el tramo
  intermedio, el estudio sobre la ENDES 2019 encontró una prevalencia más alta que en el tramo de
  menos de 1 500 m (razón de prevalencias ajustada de 1,38; IC 1,04 a 1,84)
  {ref.par("zegarra2022")}. Aquí el resultado va en sentido contrario: 0,81 (IC 0,66 a 0,98), es
  decir, una prevalencia algo menor. Los intervalos no se solapan, así que no parece un simple
  efecto del muestreo.
  <br><br>
  Es probable que intervenga más de una razón. La primera es el tiempo: entre una ola y otra
  pasaron seis años, y la composición de la población y sus condiciones de vida pueden haber
  cambiado. La segunda es el tamaño de este tramo, el menos numeroso de los tres (2 497 personas),
  cuya estimación depende más de qué conglomerados entraron en cada muestra. La tercera es la
  especificación: los dos modelos ajustan por variables parecidas pero no idénticas, y un cambio
  en los ajustes puede mover una estimación que se apoya en pocas personas. Con los datos
  disponibles no es posible distinguir entre estas explicaciones, y por eso la dejamos como una
  pregunta abierta. Lo que sí coincide en ambos estudios es el tramo alto, a partir de 2 500 m,
  donde las dos estimaciones apuntan en la misma dirección y con una magnitud parecida.
</div>

<h3>Lo que muestra el mapa, y lo que no</h3>
<p>Los dos mapas siguientes se parecen mucho. Entre los 25 departamentos, la correlación entre
la altitud media y la prevalencia es de {num(ecol_r.valor)}, y cada 1 000 m más de altitud media
se acompañan de {num(ecol_pend.valor)} puntos porcentuales más de prevalencia
({ecol_pend.detalle.replace(".", ",")}). Es un dato de grupo. Leerlo como si dijera algo sobre
cada persona que vive en esos departamentos es la <strong>falacia ecológica</strong>: una
asociación entre agregados puede no existir, o ser distinta, dentro de los individuos
{ref.par("robinson2009", "morgenstern1995")}. El mapa describe territorios, y no permite
afirmar que subir de altitud, para una persona, aumente algo.</p>

{figura(
    "mapa_04_altitud_prevalencia.png",
    "Los dos mapas se parecen, pero comparan departamentos y no personas",
    "Altitud media a la izquierda, prevalencia a la derecha. Que coincidan en la sierra "
    "sur es un dato del territorio: ahí también hay más ruralidad, menos escolaridad y, "
    "según el estudio previo con la ENDES, menos acceso a servicios de salud. Cualquiera de "
    "esas diferencias puede producir el parecido.",
    "Fuente: ENDES 2025 (INEI). Correlación de Pearson entre agregados departamentales: "
    "r = " + num(ecol_r.valor) + ". Una correlación ecológica describe grupos y no permite hablar de individuos.",
    "Dos mapas del Perú lado a lado, uno con la altitud media departamental y otro con la "
    "prevalencia de depresión. Los patrones oscuros coinciden en la sierra.")}

<h3>La altura frente al ajuste, paso a paso</h3>
<p>Para ver cuánto del gradiente se explica por quién vive allí, se ajustó la asociación de la
altitud con la depresión por etapas. La cifra es el odds ratio por cada 1 000 m de altitud: un
valor de 1,10 quiere decir que, por cada 1 000 m más, las odds de dar positivo son un 10 % más
altas.</p>

{html_tabla(tabla_pasos, {"modelo": "Ajuste", "n": "Personas", "or": "OR por 1 000 m (IC 95 %)",
                          "p": "p"}, frozenset({"n", "or", "p"}),
            "Asociación de la altitud con la depresión, desde la estimación sin ajustar hasta la ajustada. Diseño muestral "
            "complejo. Las filas con asterisco incluyen a quienes nunca asistieron a la escuela.")}

<div class="nota atencion">
  <strong>Qué se mantiene y qué se atenúa.</strong> Sin ajustar, la asociación es pequeña, con un
  odds ratio de {or_ic(c1)}, y se mantiene al tener en cuenta las características de las personas:
  {or_ic(c4)} con sexo, edad, educación, área, conductas y condiciones clínicas. Al añadir la región natural sube
  a {or_ic(c5)}, pero esa región se deriva de la propia altitud del conglomerado, así que no es un
  control independiente: es comparar dentro de franjas de altitud.
  <br><br>
  El ajuste más exigente es el departamento, que compara a personas del mismo departamento
  entre sí. Ahí el odds ratio baja a {or_ic(c6)}. El intervalo incluye al 1 y también al valor
  del modelo anterior. Lo que muestran los datos es que el gradiente aparece al comparar
  departamentos y se atenúa al comparar dentro de cada uno. Con esta muestra no es posible
  decidir entre tres lecturas: que la altitud no importa, que su efecto está mezclado con lo
  que distingue a un departamento de otro, o que dentro de un departamento hay poca variación
  de altitud para detectarlo. Con quienes nunca asistieron a la escuela incluidos, el patrón es
  el mismo: {or_ic(s1)} sin ajustar, {or_ic(s4)} ajustado y {or_ic(s6)} con departamento.
</div>

<h3>¿Por qué podría asociarse la altitud con la depresión?</h3>
<p>Hay dos clases de explicación, y es probable que no se excluyan entre sí. La primera es
biológica. Vivir a mucha altura supone una hipoxia hipobárica crónica, es decir, menos oxígeno
disponible por la menor presión atmosférica, y se ha propuesto que podría favorecer la depresión
al alterar el metabolismo de la serotonina y la bioenergética cerebral {ref.par("kious2018")}. En
modelos animales, la exposición a la altura reduce la serotonina cerebral y hace que algunos
antidepresivos pierdan eficacia {ref.par("kanekar2018")}. Y en cuatro escenarios del Perú, vivir
en altura se asoció con más síntomas depresivos, igual que tener una enfermedad respiratoria
crónica, que también implica hipoxia crónica {ref.par("zaeh2016")}. Ninguno de esos trabajos, y
menos el nuestro, demuestra que ese sea el mecanismo.</p>

<p>La segunda explicación es contextual. En nuestros datos la altura viene acompañada de más
ruralidad y menos escolaridad, y el estudio previo con la ENDES señala el acceso limitado a
servicios de salud en las zonas altas {ref.par("zegarra2022")}. En la literatura sobre suicidio y
altitud, que es un resultado distinto pero cercano, la asociación persistió al considerar la
tenencia de armas y la densidad de población {ref.par("kim2011")}, aunque una revisión concluye que
los datos agregados no bastan para estimar el efecto sobre una persona y que otros factores
individuales probablemente pesan más {ref.par("reno2018")}. Nuestro resultado va en esa línea: el
gradiente se atenúa al comparar dentro de un departamento.</p>

<p>Hay, por último, una cautela cultural y de tiempo. En adultos mayores de los Himalayas y de los
Andes, la depresión por entrevista fue poco frecuente pese a la altitud, y los autores sugieren que
la religiosidad y las redes interpersonales estrechas podrían proteger {ref.par("ishikawa2013")}.
Y el tiempo de residencia parece importar: entre médicos en formación, pasar de baja a alta altitud
se asoció con más síntomas {ref.par("kious2019")}, mientras que la ENDES no permite saber
cuánto tiempo lleva viviendo la gente donde vive {ref.par("hernandez2022")}. En conjunto, la
asociación es biológicamente plausible y probablemente se mezcla con el contexto, algo que una
encuesta de hogares no alcanza a separar.</p>

<h3>Lo que dicen los criterios de causalidad</h3>
<p>Como argumento de dosis-respuesta hay algo: por encima de los 3 000 m la prevalencia sube, y
la forma en J de la curva es más informativa que una recta. Pero no es un gradiente continuo, el
tramo intermedio baja en lugar de subir, y el gradiente se pierde al comparar dentro de un mismo
departamento. En cuanto a la temporalidad, el estudio es una foto: exposición y síntomas se
miden a la vez, de modo que no es posible establecer que vivir en la altura precede a los síntomas.
Además, la altitud es la del lugar donde la persona vive hoy y no la de donde vivió antes
{ref.par("hill1965")}. Por todo ello <strong>no se afirma que la altitud cause depresión</strong>.
Lo que hay es una asociación con gradiente en parte explicable por el contexto andino, y una
pregunta abierta bien planteada.</p>
</section>"""
    return plantilla("07-geografia.html", "Geografía", contenido, "8")


# ─────────────────────────────────────────────────────────────────────
# 9 · Factores
# ─────────────────────────────────────────────────────────────────────


def pagina_factores() -> str:
    """La confusión contada con el tabaco, los odds ratios ajustados y las interacciones."""
    bloques = tabla("tabla_21_modelos_por_bloques")
    inter = tabla("tabla_46_interacciones_filtradas")
    asoc = tabla("tabla_57_asociacion_2x2").set_index("variable")
    imp = tabla("tabla_58_riesgo_atribuible").set_index("variable")
    mh = tabla("tabla_14_confusion_mantel_haenszel")
    t22 = tabla("tabla_22_logistica_diseno_complejo").set_index("termino")
    por_sexo = tabla("tabla_68_exposicion_por_sexo")

    tab_b = bloques[bloques.variable == "fuma_12m"].iloc[0]
    alc_b = bloques[bloques.variable == "consumo_frecuente"].iloc[0]
    fu = asoc.loc["fuma_12m"]
    fu_pond = imp.loc["fuma_12m"]
    fu_mh = mh[(mh.variable == "fuma_12m") & (mh.estratificador == "Sexo")].iloc[0]
    hta_edad = mh[(mh.variable == "hta_dx") & (mh.estratificador == "Grupo etario")].iloc[0]
    alc_sexo = mh[(mh.variable == "alcohol_problematico") & (mh.estratificador == "Sexo")].iloc[0]
    fuma_h = por_sexo[(por_sexo.exposicion.str.startswith("Fumó")) & (por_sexo.sexo == "Hombres")].iloc[0]
    fuma_m = por_sexo[(por_sexo.exposicion.str.startswith("Fumó")) & (por_sexo.sexo == "Mujeres")].iloc[0]
    sobreviven = int(inter.sobrevive.sum())
    significativas = int((inter.p_homogeneidad < 0.05).sum())
    alc = t22.loc["alcohol_problematico"]
    mujer = t22.loc["es_mujer"]
    tab22 = t22.loc["fuma_12m"]
    rp_alc = imp.loc["alcohol_problematico"].rp_ajustada

    contenido = f"""<section>
{cabecera("9", "activity", "Qué se asocia con la depresión")}
<p class="entradilla">A primera vista, los datos parecen decir que fumar protege contra la
depresión. La cifra es real y la conclusión no lo es, y entender por qué es el mejor ejemplo
que tenemos de cómo una comparación sencilla puede llevarnos a una conclusión que los datos no respaldan.</p>

<h3>La paradoja del tabaco</h3>
<p>Si se comparan, sin más, las personas que fumaron en el último año con las que no, la
comparación sin ajustar sugiere que fumar protege. En la muestra sin ponderar, el
{pc(fu.prev_expuestos)} de quienes fumaron dio positivo en el tamizaje, frente al
{pc(fu.prev_no_expuestos)} de quienes no fumaron (odds ratio {num(fu["or"])}; IC 95 %
{num(fu.or_ic_inf)} a {num(fu.or_ic_sup)}). Con los pesos de la encuesta la diferencia se
reduce a {pc(fu_pond.prev_expuestos)} frente a {pc(fu_pond.prev_no_expuestos)}, con un odds
ratio sin ajustar de {num(tab_b.or_crudo)} cuyo intervalo ({num(tab_b.crudo_ic_inf)} a
{num(tab_b.crudo_ic_sup)}) ya incluye al 1. La prueba de Rao y Scott, que respeta el diseño
muestral, tampoco la sostiene (p = {fp(fu.p_rao_scott)}). En otras palabras, la comparación sin
ajustar no demuestra ninguna protección, aunque sí nos invita a mirar en esa dirección.</p>

<p>Ahora fijémonos en quién fuma. En nuestra muestra fumó en el último año el
{pc(fuma_h.prevalencia_exposicion_pct)} de los hombres y el {pc(fuma_m.prevalencia_exposicion_pct)}
de las mujeres, y las mujeres presentan más del doble de sintomatología depresiva que los
hombres. Al comparar fumadores con no fumadores estamos comparando, en buena medida, hombres con
mujeres.</p>

<p>Cuando la comparación se hace dentro de cada sexo, el resultado se da la vuelta. El odds ratio
ajustado por sexo con el método de Mantel y Haenszel es {num(fu_mh.or_mh)} (IC 95 %
{num(fu_mh.mh_ic_inf)} a {num(fu_mh.mh_ic_sup)}), y en el modelo completo, con el diseño de la
encuesta, llega a {num(tab22["or"])} (IC 95 % {num(tab22.ic_inf)} a {num(tab22.ic_sup)}). Fumar se
asocia con más sintomatología, no con menos. Es coherente con lo que se ha encontrado en otros
estudios, aunque la literatura longitudinal es menos clara sobre el sentido de la relación: hay
trabajos que van del tabaco a la depresión y otros que van de la depresión al tabaco
{ref.par("fluharty2017")}.</p>

<div class="nota atencion">
  <strong>Esto se llama confusión.</strong> Una tercera variable, aquí el sexo, se relaciona a la
  vez con la exposición y con el resultado, y distorsiona la comparación hasta invertirla. Algo
  parecido le ocurre al consumo frecuente de alcohol: con el diseño de la encuesta su odds ratio
  sin ajustar es {num(alc_b.or_crudo)} y pasa a {num(alc_b.or_ajustado)} al ajustar. De las seis
  exposiciones que examinamos, dos cambian de dirección. La sección 13 explica con más detalle
  cómo entendemos y controlamos la confusión.
</div>

{figura(
    "fig_07_confusion.png",
    "Ajustar no es un trámite: en algunos casos cambia el signo del resultado",
    "Antes de comparar dos grupos conviene descontar aquello que los diferencia por otras "
    "razones. Cada barra corresponde a un factor y a una variable que podía distorsionar su "
    "medición, como la edad o el sexo, y su longitud dice cuánto se mueve el resultado al "
    "descontarla: mientras más larga, más distorsionaba la comparación sin ajustar. El 10 % es el umbral "
    "convencional, y por debajo de él se considera que la distorsión no era relevante. Muchas "
    f"barras lo superan: la hipertensión cambia un {abs(hta_edad.cambio_pct):.0f} % al tener en "
    f"cuenta la edad, y el consumo problemático de alcohol un {abs(alc_sexo.cambio_pct):.0f} % "
    "al tener en cuenta el sexo.",
    "Fuente: ENDES 2025 (INEI). Comparación entre el odds ratio sin ajustar y el ajustado por "
    "Mantel y Haenszel. El umbral del 10 % sigue a "
    + ref.par("maldonado1993", "mickey1989") + ".",
    "Gráfico de barras horizontales con el cambio porcentual entre el odds ratio sin ajustar y el "
    "ajustado. Las barras que superan el umbral del 10 % aparecen destacadas.")}

<h3>El panorama completo</h3>
{figura(
    "fig_11_forest_or_ajustados.png",
    "El consumo problemático de alcohol tiene la asociación más fuerte del modelo",
    "La línea vertical punteada marca el 1, donde no hay asociación. Un punto a la derecha "
    "indica que la sintomatología es más frecuente con ese factor y uno a la izquierda, que lo "
    "es menos; la línea horizontal de cada punto es su margen de error, y si cruza el 1, los "
    "datos no permiten afirmar que exista asociación. "
    f"Con un odds ratio ajustado de {num(alc['or'])} (una razón de prevalencias ajustada de "
    f"{num(rp_alc)}), el consumo problemático de alcohol es el factor de mayor fuerza, por "
    f"delante del sexo femenino ({num(mujer['or'])}). Vivir en la selva aparece del otro lado, "
    "con menos sintomatología que vivir en la costa. Los puntos grises son los que no permiten "
    "concluir nada, justamente porque su intervalo incluye el valor sin asociación. La sección "
    "10 compara cada una de estas asociaciones con lo que se ha publicado.",
    "Fuente: ENDES 2025 (INEI). Odds ratios ajustados por todas las variables del modelo "
    "(sexo, edad, educación, área, región natural, alcohol, tabaco, hipertensión, diabetes y "
    "obesidad), con el diseño muestral complejo. n = 28 553.",
    "Gráfico de puntos con líneas horizontales. El consumo problemático de alcohol tiene el "
    "valor más alto, alrededor de 6. El sexo femenino ronda 3. La selva aparece por debajo "
    "de 1.")}

<h3>Cuándo una asociación no es igual para todos</h3>
<p>Con 30 000 observaciones, las pruebas estadísticas detectan diferencias muy pequeñas. De las
{len(inter)} combinaciones que examinamos, {significativas} salían «significativas», y eso no
quiere decir que las {significativas} sean relevantes.</p>

<p>Por eso pedimos tres condiciones a la vez: que la diferencia siga siendo significativa tras
corregir por el número de pruebas, que los odds ratios de los dos grupos difieran al menos vez y
media, y que ambos grupos tengan casos suficientes. <strong>Sobreviven {sobreviven}.</strong></p>

{html_tabla(inter[inter.sobrevive][["exposicion", "estratificador", "razon_or",
                                    "eventos_min_celda", "p_fdr"]].head(10),
            {"exposicion": "Exposición", "estratificador": "Difiere según",
             "razon_or": "Cuánto difieren", "eventos_min_celda": "Casos en la celda más pequeña",
             "p_fdr": "p corregido"},
            frozenset({"razon_or", "eventos_min_celda", "p_fdr"}),
            "Las interacciones que superan los tres criterios a la vez.")}

<div class="nota">
  <strong>Por qué un valor p pequeño no basta.</strong> Con una muestra grande, casi cualquier
  diferencia sale «estadísticamente significativa», incluso una que no cambiaría ninguna decisión.
  Lo que importa es el tamaño de la diferencia, y eso conviene mirarlo aparte. La sección
  siguiente lo hace: mide qué tan fuerte es cada asociación y a cuánta gente alcanza.
</div>
</section>"""
    return plantilla("08-factores.html", "Factores asociados", contenido, "9")



# ─────────────────────────────────────────────────────────────────────
# 10 · Medidas de asociación y riesgo atribuible
# ─────────────────────────────────────────────────────────────────────


def pagina_asociacion() -> str:
    """Tabla 2×2, razón de prevalencias, odds ratio, chi cuadrado y riesgo atribuible."""
    a = tabla("tabla_57_asociacion_2x2")
    imp = tabla("tabla_58_riesgo_atribuible").set_index("variable")
    t22 = tabla("tabla_22_logistica_diseno_complejo").set_index("termino")
    t27 = tabla("tabla_27_modelo_subpoblacion_violencia").set_index("termino")
    pasos = tabla("tabla_60_altitud_cruda_vs_ajustada").set_index("modelo")

    def or_aj(v: str) -> pd.Series:
        return t27.loc[v] if v == "violencia_fisica" else t22.loc[v]

    def fmt_or(r: pd.Series) -> str:
        return f"{num(r['or'])} ({num(r.ic_inf)} a {num(r.ic_sup)})"

    # Tabla de las celdas a, b, c, d
    celdas = pd.DataFrame({
        "factor": a.exposicion,
        "a": [f"{int(x):,}".replace(",", " ") for x in a.a],
        "b": [f"{int(x):,}".replace(",", " ") for x in a.b],
        "c": [f"{int(x):,}".replace(",", " ") for x in a.c],
        "d": [f"{int(x):,}".replace(",", " ") for x in a.d],
        "con": [pc(x) for x in a.prev_expuestos],
        "sin": [pc(x) for x in a.prev_no_expuestos],
    })
    # Tabla de las medidas
    medidas = pd.DataFrame({
        "factor": a.exposicion,
        "rp": a.rp_formato.str.replace(".", ",", regex=False),
        "or": a.or_formato.str.replace(".", ",", regex=False),
        "chi": [f"{num(x)} ({fp(p)})" for x, p in zip(a.chi2, a.p_chi2, strict=False)],
        "rs": [fp(p) for p in a.p_rao_scott],
        "orajust": [fmt_or(or_aj(v)) if v in t22.index or v in t27.index else "—" for v in a.variable],
        "lectura": [x[0].upper() + x[1:] for x in a.lectura],
    })

    # Medidas de impacto: solo se muestran donde admiten lectura
    filas = []
    for v in ["es_mujer", "violencia_fisica", "hta_dx", "fuma_12m", "alcohol_problematico",
              "diabetes_dx", "obesidad", "consumo_frecuente", "es_rural"]:
        r = imp.loc[v]
        ok = bool(r.interpretable)
        filas.append({
            "factor": r.exposicion + (" *" if v == "violencia_fisica" else ""),
            "pe": pc(r.prev_exposicion),
            "rp": f"{num(r.rp_ajustada, 2)} ({num(r.rp_ajustada_ic_inf, 2)} a {num(r.rp_ajustada_ic_sup, 2)})",
            "rd": f"{num(r.rd, 1)}",
            "afe": pc(r.afe_ajustada) if ok else "—",
            "paf": (f"{num(r.paf_ajustada)} ({num(r.paf_ajustada_ic_inf)} a {num(r.paf_ajustada_ic_sup)})"
                    if ok else "—"),
        })
    impacto = pd.DataFrame(filas)

    alc, viol, hta = imp.loc["alcohol_problematico"], imp.loc["violencia_fisica"], imp.loc["hta_dx"]
    fum, sex = imp.loc["fuma_12m"], imp.loc["es_mujer"]
    c4 = next(i for i in pasos.index if i.startswith("(4)") and "*" not in i)
    f4 = pasos.loc[c4]

    contenido = f"""<section>
{cabecera("10", "trending-up", "Qué tan fuerte es una asociación y a cuánta gente alcanza")}
<p class="entradilla">Una asociación se puede medir de dos maneras: qué tan fuerte es y cuánta gente
involucra. Son cosas distintas, y conviene no mezclarlas para no sacar conclusiones que los datos
no respaldan.</p>

<h3>Por qué hablamos de prevalencia y de razón de prevalencias</h3>
<p>La ENDES entrevistó a cada persona una sola vez. Lo que se puede contar, entonces, es la
<strong>prevalencia</strong>: cuántas personas tienen síntomas en el momento de la encuesta. La
<em>incidencia</em>, es decir, cuántas personas desarrollan síntomas con el paso del tiempo, exige
seguir a la gente, y eso no se hizo. Un estudio transversal sirve para medir prevalencia y no
permite distinguir qué fue primero {ref.par("mann2003")}.</p>

<p>El riesgo relativo clásico se calcula con incidencias, de modo que aquí no lo calculamos. Usamos
su equivalente para una fotografía, la <strong>razón de prevalencias</strong>: el cociente entre
la prevalencia de quienes tienen un factor y la de quienes no lo tienen. Para estimarla con un
ajuste por otras variables se recomienda la regresión de Poisson con varianza robusta
{ref.par("zou2004", "barros2003")}. Junto a ella damos el <strong>odds ratio</strong>, que es lo
que estima la regresión logística del modelo principal.</p>

<h3>Cada factor en una tabla 2×2</h3>
<p>Para cada factor, las personas se reparten en cuatro casillas: <strong>a</strong>, con el factor
y con sintomatología; <strong>b</strong>, con el factor y sin ella; <strong>c</strong>, sin el
factor y con sintomatología; y <strong>d</strong>, sin el factor y sin ella. De ahí salen las
prevalencias de cada grupo y todas las medidas que siguen. Esta tabla cuenta a las personas
entrevistadas sin ponderar, como se hace al presentar una 2×2.</p>

{html_tabla(celdas, {"factor": "Factor", "a": "a", "b": "b", "c": "c", "d": "d",
                     "con": "Prevalencia con el factor", "sin": "Prevalencia sin el factor"},
            frozenset({"a", "b", "c", "d", "con", "sin"}),
            "Tablas 2×2 de cada factor, con las personas entrevistadas sin ponderar. En la "
            "violencia física de pareja solo entran quienes tuvieron pareja.")}

<p>La razón de prevalencias (RP) y el odds ratio (OR) se leen así: un valor de 1 quiere decir que
la prevalencia es la misma con y sin el factor; por encima de 1, que es más alta con el factor, y
por debajo, que es más baja. Cada una lleva su intervalo de confianza al 95 %. La columna de la
derecha traduce el resultado en una línea, como factor de riesgo o factor protector, y con qué
intensidad (discreta por debajo de 1,5; moderada hasta 3; marcada desde 3, una convención práctica y no una
norma).</p>

{html_tabla(medidas, {"factor": "Factor", "rp": "RP (IC 95 %)", "or": "OR (IC 95 %)",
                      "chi": "χ² (p)", "rs": "p de Rao y Scott",
                      "orajust": "OR ajustado del modelo", "lectura": "Lectura"},
            frozenset({"rp", "or", "chi", "rs", "orajust"}),
            "Medidas de asociación sin ajustar (sin ponderar) y OR ajustado del modelo con diseño "
            "complejo. La lectura exige que la asociación sobreviva al diseño muestral.")}

<h3>Qué dice la prueba chi cuadrado</h3>
<p>Junto a cada 2×2 va la prueba chi cuadrado de Pearson, con un grado de libertad. Su hipótesis
nula es que el factor y la sintomatología no se asocian, es decir, que la prevalencia es la misma
con y sin el factor. Un valor p pequeño indica que, si esa hipótesis fuera cierta, los datos
observados serían poco esperables, y por eso la ponemos en duda.</p>

<p>Esa prueba trata a todas las personas como si fueran independientes, y en una encuesta por
conglomerados no lo son. La versión de Rao y Scott corrige el estadístico por el efecto del diseño
{ref.par("rao1984")}, y esa diferencia cambia la lectura. En el área rural, Pearson sugiere una señal pequeña, y con
el diseño desaparece (p = {fp(a.set_index("variable").loc["es_rural"].p_rao_scott)}). Algo parecido
ocurre con el tabaco, cuya asociación sin ajustar ya no se sostiene al respetar el diseño. Por eso la
columna de la lectura se apoya en la prueba de Rao y Scott y no en la de Pearson.</p>

{figura(
    "fig_06_or_vs_rp.png",
    "El odds ratio se aleja un poco más del 1, aunque aquí la diferencia es pequeña",
    "Cada factor aparece medido de dos maneras, el odds ratio y la razón de prevalencias, y "
    "cuanto más se separan los dos puntos de un mismo factor, más difieren esas dos formas de "
    "contar lo mismo. El odds ratio siempre se aleja más del 1 que la razón de prevalencias, y "
    "la diferencia crece cuando la condición es más frecuente. Con una prevalencia del 7 % la "
    "teoría dice que deberían parecerse, y aquí casi coinciden: la distancia media es del "
    "5,3 %. Nos pareció mejor comprobarlo con los propios datos que quedarnos con lo que dice el manual. Cuando "
    "la condición es poco frecuente, el odds ratio puede leerse de forma aproximada como una "
    "razón de prevalencias "
    + ref.par("barros2003") + ".",
    "Fuente: ENDES 2025 (INEI). La razón de prevalencias se estimó con regresión de Poisson "
    "y varianza robusta.",
    "Gráfico de puntos que compara el odds ratio con la razón de prevalencias de cada "
    "exposición. Los puntos se alinean cerca de la diagonal.")}

<h3>Qué dice la literatura de cada asociación</h3>
<p>Ninguno de estos resultados está solo. Los hemos puesto junto a lo que se ha publicado, y
conviene leer la comparación con cuidado: otros estudios usan otras definiciones, otras edades y
otros diseños, y en muchos casos miden una relación a lo largo del tiempo que aquí no podemos
observar.</p>

{html_tabla(pd.DataFrame([
    {"f": "Sexo femenino", "n": fmt_or(t22.loc["es_mujer"]),
     "l": f"Una revisión de más de 90 países halló un OR global de 1,95, con el máximo en la "
          f"adolescencia y estable en la adultez {ref.par('salk2017')}. En el Perú, ser hombre "
          f"se asoció con una razón de prevalencias de 0,50 {ref.par('basauri2025')}.",
     "c": "La brecha es más amplia que el promedio internacional. Con estos datos no es "
          "posible establecer el motivo."},
    {"f": "Violencia física de pareja", "n": fmt_or(t27.loc["violencia_fisica"]),
     "l": f"En mujeres, los estudios de seguimiento muestran una asociación con síntomas "
          f"depresivos posteriores (OR agrupado de 1,97) y también en sentido contrario, de los "
          f"síntomas a la violencia posterior (1,93) {ref.par('devries2013')}.",
     "c": "Asociación fuerte y plausible, probablemente en los dos sentidos. Nuestra cifra es "
          "más alta, y puede deberse a que mide prevalencia en una foto y reúne a hombres y mujeres."},
    {"f": "Consumo problemático de alcohol", "n": fmt_or(t22.loc["alcohol_problematico"]),
     "l": f"Con trastorno por consumo de alcohol, las odds de depresión se duplican (OR "
          f"agrupado de 2,00 a 2,09), y la relación más verosímil va del alcohol a la depresión "
          f"{ref.par('boden2011')}.",
     "c": "Nuestra cifra es mayor y su intervalo es amplio, porque lo declaran 304 personas. Dos "
          "criterios de abuso no equivalen a un trastorno por consumo."},
    {"f": "Hipertensión diagnosticada", "n": fmt_or(t22.loc["hta_dx"]),
     "l": f"Una razón de prevalencias de 1,45 en otro análisis peruano {ref.par('basauri2025')}. "
          f"En cohortes, la depresión precede a la hipertensión (riesgo relativo de 1,42) "
          f"{ref.par('meng2012')}.",
     "c": "Misma magnitud que en el estudio peruano. El sentido puede ir de la depresión a la "
          "hipertensión."},
    {"f": "Diabetes diagnosticada", "n": fmt_or(t22.loc["diabetes_dx"]),
     "l": f"Una razón de prevalencias de 1,42 en otro análisis peruano {ref.par('basauri2025')}. "
          f"La relación es bidireccional: diabetes a depresión, 1,15; depresión a diabetes, 1,60 "
          f"{ref.par('mezuk2008')}.",
     "c": "Coincide con el estudio peruano. Con una foto no se sabe cuál precede."},
    {"f": "Fumó en los últimos 12 meses", "n": fmt_or(t22.loc["fuma_12m"]),
     "l": f"Una razón de prevalencias de 1,32 para quien fuma cada mes {ref.par('basauri2025')}. "
          f"Los estudios longitudinales encuentran asociaciones en ambos sentidos y no "
          f"coinciden en cuál pesa más {ref.par('fluharty2017')}.",
     "c": "Sentido coherente. La paradoja de la sección 9 muestra cuánto depende de ajustar "
          "por sexo."},
    {"f": "Obesidad (IMC de 30 o más)", "n": fmt_or(t22.loc["obesidad"]),
     "l": f"En estudios longitudinales, la obesidad se asocia con depresión posterior (OR de 1,55) "
          f"y la depresión con obesidad posterior (1,58) {ref.par('luppino2010')}.",
     "c": "Nuestra asociación es más moderada y su intervalo incluye al 1. No contradice la "
          "literatura, pero tampoco la confirma con estos datos."},
    {"f": "Área rural", "n": fmt_or(t22.loc["es_rural"]),
     "l": f"Una razón de prevalencias de 0,85 en otro análisis peruano {ref.par('basauri2025')}. "
          f"Los trastornos del ánimo son algo más frecuentes en zonas urbanas {ref.par('peen2010')}.",
     "c": "Coincide en el sentido. Sin ajustar, las prevalencias rural y urbana casi no difieren "
          "(6,8 % y 7,0 %)."},
    {"f": "Primaria o menos, frente a educación superior", "n": fmt_or(t22.loc["educacion_grupo_Primaria o menos"]),
     "l": f"El nivel socioeconómico bajo se asocia con más depresión (OR de 1,81), con una "
          f"relación dosis-respuesta para la educación y el ingreso {ref.par('lorant2003')}.",
     "c": "Coincide, y la prevalencia baja de forma ordenada con cada nivel (8,8 %, 7,0 % y 5,3 %)."},
    {"f": "Altitud (por cada 1 000 m)", "n": f"{num(f4.or_por_1000m)} ({num(f4.ic_inf)} a {num(f4.ic_sup)})",
     "l": f"Mayor puntaje depresivo con cada 100 m de altitud en la ENDES de 2013 a 2020 "
          f"{ref.par('hernandez2022')}, y una razón de prevalencias de 1,41 a partir de 2 500 m en "
          f"la de 2019 {ref.par('zegarra2022')}.",
     "c": "Coincide con el ajuste por las personas, pero se atenúa al comparar dentro de un mismo "
          "departamento (sección 8)."},
]), {"f": "Factor", "n": "Nuestro OR ajustado (IC 95 %)", "l": "Lo que se ha publicado",
     "c": "Cómo lo leemos"}, frozenset({"n"}),
   "Contraste entre nuestros resultados y la literatura. Los estudios citados difieren en "
   "definiciones, edades y diseños.")}

<h3>Cuánto pesa cada factor en la población</h3>
<p>Una asociación fuerte no es lo mismo que un gran impacto. Para ver la diferencia se usan tres
medidas que parten de la prevalencia y no de la incidencia, y que por eso conviene leer con
cuidado:</p>

<ul>
  <li>La <strong>diferencia de prevalencias</strong> entre quienes tienen el factor y quienes no, en
  puntos porcentuales.</li>
  <li>La <strong>fracción atribuible en los expuestos</strong>: de las personas con el factor que
  dieron positivo, qué parte correspondería al factor.</li>
  <li>La <strong>fracción atribuible poblacional</strong>, la más útil en salud pública: qué parte
  de todos los casos de la población se asocia con el factor. Depende de la fuerza de la
  asociación y también de cuán frecuente sea el factor {ref.par("miettinen1974", "rockhill1998")}.</li>
</ul>

<p>Las dos fracciones solo significan «casos que no ocurrirían» si la asociación fuera causal y
no estuviera confundida, y este diseño no permite comprobarlo. Por eso las llamamos fracciones
atribuibles y no fracciones evitables. Se calcularon con los pesos de la encuesta y con la razón
de prevalencias ajustada por las mismas variables del modelo principal, y sus intervalos salen de
un remuestreo de conglomerados dentro de estratos {ref.par("rao1988")}.</p>

{html_tabla(impacto, {"factor": "Factor", "pe": "Personas con el factor", "rp": "RP ajustada (IC 95 %)",
                      "rd": "Diferencia sin ajustar (puntos)", "afe": "Fracción en expuestos",
                      "paf": "Fracción poblacional, % (IC 95 %)"},
            frozenset({"pe", "rp", "rd", "afe", "paf"}),
            "Medidas de impacto basadas en prevalencia. Se omite la fracción cuando, tras "
            "ajustar, la asociación no se distingue de la nulidad o resulta protectora. "
            "* Entre quienes tuvieron pareja.")}

{figura(
    "fig_19_fuerza_e_impacto.png",
    "La asociación más fuerte no es la que alcanza a más gente",
    "El panel de la izquierda mide qué tan fuerte es la asociación y el de la derecha, cuántos "
    "casos de la población involucra, con un factor en cada fila. Un factor puede ser fuerte y "
    "poco frecuente, y entonces involucra a pocos casos. "
    f"El consumo problemático de alcohol tiene la razón de prevalencias más alta "
    f"({num(alc.rp_ajustada, 2)}) y, sin embargo, una fracción poblacional de solo "
    f"{pc(alc.paf_ajustada)}, porque lo declara apenas el {pc(alc.prev_exposicion)} de la "
    f"población. La hipertensión, con una asociación moderada ({num(hta.rp_ajustada, 2)}), "
    f"involucra al {pc(hta.paf_ajustada)} de los casos porque la tiene alrededor del "
    f"{pc(hta.prev_exposicion, 0)} de la gente. Las fracciones de distintos factores no se "
    "suman, porque una misma persona puede tener varios a la vez.",
    "Fuente: ENDES 2025 (INEI). Pesos de la encuesta; IC 95 % por remuestreo de conglomerados "
    "(RP: varianza de Taylor). La violencia se estima entre quienes tuvieron pareja. No implica "
    "causalidad.",
    "Dos paneles con cinco factores. A la izquierda, las razones de prevalencias ajustadas: la "
    "violencia y el consumo problemático de alcohol son las más altas. A la derecha, las "
    "fracciones atribuibles: la violencia es la mayor y el alcohol, de las menores.")}

<div class="nota">
  <strong>En palabras sencillas.</strong> Si estas asociaciones fueran causales, y solo en ese
  caso, evitar la violencia física de pareja se asociaría con cerca de {num(viol.paf_ajustada, 0)}
  de cada 100 casos entre quienes tienen o tuvieron pareja; la hipertensión, con unos
  {num(hta.paf_ajustada, 0)} de cada 100; fumar, con unos {num(fum.paf_ajustada, 0)}; y el
  consumo problemático de alcohol y la diabetes, con unos {num(alc.paf_ajustada, 0)} de cada 100 cada
  uno. El sexo femenino reúne la fracción mayor ({pc(sex.paf_ajustada, 0)}), pero no es una
  exposición que pueda modificarse: señala dónde se concentra la carga, no qué se puede evitar.
  En la diabetes el intervalo llega a cero, así que su fracción es la menos firme.
</div>

<p>Esta diferencia entre fuerza y alcance es la misma que aparece en la sección 12, donde el
alcohol problemático encabeza el ranking por efecto y ocupa un lugar bajo por utilidad predictiva.
Son dos formas de decir que un efecto grande sobre muy poca gente apenas mueve el panorama general.</p>
</section>"""
    return plantilla("09-asociacion.html", "Fuerza e impacto", contenido, "10")


# ─────────────────────────────────────────────────────────────────────
# 11 · Validez interna: sesgos y límites
# ─────────────────────────────────────────────────────────────────────


def pagina_validez() -> str:
    """Sesgos de selección, de información y de confusión aplicados a este estudio."""
    flujo = tabla("tabla_04_flujograma_strobe")
    nr = tabla("tabla_65_resultado_entrevista_phq9").set_index("resultado")
    perfil_nr = tabla("tabla_66_perfil_sin_phq9").set_index("indicador")
    sin_edu = tabla("tabla_63_perfil_sin_educacion").set_index("indicador")
    comp = tabla("tabla_64_modelo_con_sin_educacion")
    conf = tabla("tabla_59_altitud_confusor_de_otros_factores")

    sin_phq = int(flujo.excluidos.iloc[1])
    total = int(flujo.n.iloc[0])
    urbano_sin = 100 - perfil_nr.loc["area_rural_pct", "sin_phq9"]
    urbano_con = 100 - perfil_nr.loc["area_rural_pct", "con_phq9"]
    alt_sin = perfil_nr.loc["altitud_media_m", "sin_phq9"]
    alt_con = perfil_nr.loc["altitud_media_m", "con_phq9"]
    se = sin_edu["sin_educacion"]
    rs = sin_edu["resto"]
    fila_sin = comp[comp.etiqueta.str.startswith("Sin educación")].iloc[0]
    cambio_max = comp.cambio_pct.abs().max()
    n_terminos = int(comp.cambio_pct.notna().sum())

    def miles(n: float) -> str:
        return f"{round(n):,}".replace(",", " ")

    tabla_conf = pd.DataFrame({
        "factor": conf.exposicion,
        "sin": [f"{num(x)} ({num(lo)} a {num(hi)})" for x, lo, hi in
                zip(conf.or_sin_altitud, conf.sin_ic_inf, conf.sin_ic_sup, strict=False)],
        "con": [f"{num(x)} ({num(lo)} a {num(hi)})" for x, lo, hi in
                zip(conf.or_con_altitud, conf.con_ic_inf, conf.con_ic_sup, strict=False)],
        "cambio": [num(x, 1) for x in conf.cambio_pct],
        "cambio_sr": [num(x, 1) if pd.notna(x) else "—" for x in conf.cambio_sin_region_pct],
    })
    mayor_sr = conf.cambio_sin_region_pct.abs().max()
    mayor = conf.cambio_pct.abs().max()
    sr_cual = conf.loc[conf.cambio_sin_region_pct.abs().idxmax(), "exposicion"].lower()

    contenido = f"""<section>
{cabecera("13", "shield-check", "Qué puede mover estas cifras")}
<p class="entradilla">Una cifra vale tanto como el proceso que la produjo: quién entró a la
encuesta, cómo se midió cada cosa y qué se comparó con qué. Esta sección repasa con calma los tres
tipos de error que pueden mover nuestros resultados, qué creemos que hacen en este estudio y qué
hicimos al respecto.</p>

<h3>Quién entra y quién no: el sesgo de selección</h3>
<p>Hay sesgo de selección cuando las personas que llegan al análisis no representan a las que
interesan, y la diferencia tiene que ver a la vez con lo que se estudia y con el resultado
{ref.par("hernan2004")}. En esta encuesta hay tres puertas por donde puede entrar.</p>

<p>La primera es el universo. La ENDES entrevista a los hogares particulares y a sus miembros, y
el cuestionario de salud lo responde una persona de 15 años o más elegida en cada hogar
{ref.par("inei2026")}. Quedan fuera quienes no viven en un hogar particular. Si la sintomatología
depresiva fuera más frecuente entre ellos, la prevalencia que estimamos quedaría algo por debajo
de la real. Dentro del universo, la cobertura fue alta: se ejecutaron 36 750 de las 36 760
viviendas programadas, y los ponderadores se ajustan por la no respuesta de las viviendas
{ref.par("inei2026")}.</p>

<p>La segunda es la no respuesta de cada persona, que es la que más nos ocupa. De las
{miles(total)} personas que entraron al cuestionario de salud, {miles(sin_phq)}
({pc(sin_phq / total * 100)}) no tienen el PHQ-9 completo: {miles(nr.loc["Ausente", "sin_phq9"])} no
estaban, {miles(nr.loc["Rechazada", "sin_phq9"])} rechazaron,
{miles(nr.loc["Incompleta", "sin_phq9"])} dejaron la entrevista a medias,
{miles(nr.loc["Discapacitada(o)", "sin_phq9"])} tenían una discapacidad que lo impidió y
{miles(nr.loc["Otra", "sin_phq9"])} salieron por otro motivo. De ellas sabemos poco: su sexo y su
edad no figuran en el archivo. Lo que sí sabemos por el registro del hogar es que son más
urbanas ({pc(urbano_sin, 0)} frente a {pc(urbano_con, 0)}) y viven algo más abajo
({miles(alt_sin)} m en promedio frente a {miles(alt_con)} m). Con eso no se puede decir hacia dónde
mueven la prevalencia: si quienes no estaban o no quisieron responder tuvieran más síntomas, la
estaríamos subestimando; si tuvieran menos, la estaríamos sobreestimando.</p>

<p>La tercera es nuestro propio recorte. El análisis con casos completos deja fuera a
{miles(se.loc["Personas en el análisis"])} personas con el nivel educativo ausente. No son datos
perdidos al azar: el cuestionario pregunta primero si la persona asistió a la escuela y solo
después, a quienes asistieron, por el nivel aprobado, de modo que estas personas son quienes nunca
asistieron. Son en su mayoría mujeres ({pc(se.loc["Mujeres (%)"], 0)}), de
{num(se.loc["Edad media (años)"], 0)} años en promedio, que viven en el área rural
({pc(se.loc["Área rural (%)"], 0)}) y a más altitud ({miles(se.loc["Altitud media del conglomerado (m)"])} m
frente a {miles(rs.loc["Altitud media del conglomerado (m)"])} m), y su prevalencia ponderada es de
{pc(se.loc["Prevalencia ponderada (%)"])} (IC 95 % {num(se.loc["IC 95 % inferior"], 1)} a
{num(se.loc["IC 95 % superior"], 1)}), más del doble que la del resto
({pc(rs.loc["Prevalencia ponderada (%)"])}).</p>

<p>Para medir cuánto importa su ausencia repetimos el modelo principal incluyéndolas como una
categoría más. Ninguno de los {n_terminos} coeficientes comparables cambió un 10 % o más (el mayor
fue de {pc(cambio_max)}), y la categoría «sin educación» tiene un odds ratio de
{num(fila_sin.or_con_sin_educacion)} frente a la educación superior. Mantenemos el modelo con casos
completos como análisis principal y presentamos esta comparación como análisis de sensibilidad. La
conclusión es doble: la exclusión no altera lo que se asocia con la depresión en los factores
principales, y deja fuera a un grupo especialmente afectado, cuya ausencia sí puede debilitar la
asociación sin ajustar de la altitud (sección 8).</p>

<h3>Cómo se midió: el sesgo de información</h3>
<p>Es el que más pesa en este estudio. El PHQ-9 es un autorreporte, y todo autorreporte sobre temas sensibles
puede teñirse de deseabilidad social, esa tendencia a responder lo que parece más aceptable
{ref.par("krumpal2013")}. Además, define un caso por tamizaje y no por diagnóstico clínico. Frente a
una entrevista diagnóstica, con el corte en 10 el cuestionario tiene una sensibilidad de 0,88 y una
especificidad de 0,85 {ref.par("levis2019")}: algunas personas con el trastorno no alcanzan el
puntaje y otras sin él sí lo hacen. Cuando la condición es poco frecuente, esos falsos positivos
pesan mucho, y por eso hablamos de tamizaje positivo y no de depresión.</p>

<p>El error de clasificación podría no ser igual entre grupos, por ejemplo entre hombres y mujeres,
entre el campo y la ciudad o entre quienes viven a distinta altura. En ese caso distorsiona las
comparaciones en una dirección que no se conoce de antemano. Con datos de la ENDES se encontró que
el PHQ-9 mide lo mismo según sexo, edad, nivel educativo, nivel socioeconómico, estado civil y área
de residencia {ref.par("villarreal2019")}, lo que tranquiliza sobre la estructura del instrumento.
No resuelve, sin embargo, si el punto de corte clasifica igual en todos los grupos. Un estudio en
adultos mayores de los Himalayas y los Andes ilustra la diferencia entre tamizar y entrevistar: un
tamizaje breve dio positivo en entre 5,3 % y 36,9 % según el lugar, mientras que la entrevista
psiquiátrica encontró entre 1,8 % y 2,9 % de depresión en todos {ref.par("ishikawa2013")}.</p>

<p>El bloque de alcohol de la encuesta salta la pregunta siguiente cuando la respuesta es «sí», de
modo que contar los ítems tal como vienen penalizaría a los casos más graves, cuyo dato faltante significa «ya
cumplió el criterio». Lo resolvimos agrupando por criterio con lógica «o». Es una decisión razonada,
pero no contrastada con una medida de referencia, y deja un margen de error de medición en el
consumo problemático, que es justamente el factor de mayor fuerza. Si ese error fuera igual entre
quienes tienen y no tienen síntomas, lo esperable sería que acercara la asociación al 1, aunque ni
siquiera eso está garantizado en un estudio concreto {ref.par("jurek2005")}.</p>

<p>La hipertensión y la diabetes son diagnósticos que informa la persona, y para recibirlos hay que
haber llegado a un servicio de salud. Quien tiene menos acceso puede estar sin diagnóstico aunque
tenga la enfermedad. Ese efecto no se puede medir con estos datos, y es una razón más para leer
esas asociaciones con prudencia. La obesidad, en cambio, se calcula con el peso y la talla medidos por el
entrevistador.</p>

<h3>Qué se compara con qué: la confusión</h3>
<p>Un factor confunde una asociación cuando cumple tres condiciones a la vez: es factor de riesgo
del evento, se asocia con la exposición y no es un eslabón intermedio en la cadena causal entre
ambos. El sexo, en la paradoja del tabaco de la sección 9, es el ejemplo más claro. Lo controlamos
de dos maneras: estratificando, es decir, comparando dentro de cada grupo con el método de Mantel y
Haenszel, y ajustando en el modelo multivariable. Para decidir qué entra al modelo nos apoyamos en un
diagrama causal {ref.par("greenland1999")}, y para declarar que hay confusión usamos el criterio del
cambio de 10 % en la estimación {ref.par("maldonado1993", "mickey1989")}. Los factores que podrían
estar en el camino entre una exposición y la depresión, como la obesidad, no se ajustan como
confusores sino que se estudian aparte, en la sección 11.</p>

{figura(
    "fig_08_dag_causal.png",
    "Qué se ajusta y qué no, dicho antes de modelar",
    "El diagrama declara los supuestos del estudio antes de ver los resultados. Sexo, edad, "
    "educación y área se ajustan porque preceden a las exposiciones y al desenlace; el "
    "tratamiento recibido no se ajusta porque es consecuencia de la depresión, y ajustarlo "
    "introduciría otro sesgo.",
    "Fuente: elaboración propia. Los supuestos causales son una hipótesis de trabajo y no una "
    "demostración.",
    "Diagrama con cuatro confusores a la izquierda, cuatro exposiciones en el centro, la "
    "depresión a la derecha y el tratamiento recibido como consecuencia de la depresión.")}

<h3>La altitud como posible confusor</h3>
<p>La altitud no viaja sola, y por eso nos preguntamos si confunde a los demás factores. La
respuesta se mide con el mismo criterio: se compara el odds ratio de cada factor sin y con la
altitud en el modelo. La altitud entra por pisos y no como recta, porque su relación con la depresión
tiene forma de J.</p>

{html_tabla(tabla_conf, {"factor": "Factor", "sin": "OR sin altitud (IC 95 %)",
                         "con": "OR con altitud (IC 95 %)", "cambio": "Cambio (%)",
                         "cambio_sr": "Cambio sin región natural (%)"},
            frozenset({"sin", "con", "cambio", "cambio_sr"}),
            "Odds ratio de cada factor sin y con ajuste por piso altitudinal, con el diseño "
            "muestral complejo. El cambio se calcula sobre el odds ratio.")}

<p>La altitud <strong>no confunde</strong> a ninguno de los factores principales. Al añadirla al
modelo, el odds ratio cambia como máximo un {pc(mayor)}, muy por debajo del 10 %. Como la región
natural se deriva de la propia altitud y podría estar absorbiendo parte de su efecto, se repitió la
comparación sin ella: el mayor cambio es de {pc(mayor_sr)} ({sr_cual}), también por debajo del
umbral. La razón de prevalencias se comporta igual. Por eso las asociaciones que presenta el
boletín se mantienen con o sin la altitud en el modelo.</p>

{figura(
    "fig_20_altitud_confusor.png",
    "Añadir la altitud casi no mueve a los demás factores",
    "A la izquierda, cada factor aparece dos veces: sin la altitud en el modelo (punto lleno) "
    "y con ella (punto hueco). Mientras más separados estén los dos puntos de un factor, más "
    "lo movía la altitud; aquí casi coinciden, y eso es el resultado: la altitud no altera lo "
    "que se asocia con la depresión en esos factores. A la derecha, cada fila añade un ajuste "
    "al gradiente de la propia altitud, y la última compara solo dentro de cada departamento, "
    "donde el intervalo ya cruza el 1. Ese panel se discute en la sección 8.",
    "Fuente: ENDES 2025 (INEI). Diseño muestral complejo.",
    "Dos paneles. A la izquierda, pares de puntos casi superpuestos para nueve factores. A la "
    "derecha, odds ratios por cada 1 000 metros en seis modelos, con el último intervalo "
    "cruzando el 1.")}

<p>Queda un límite que conviene decir con franqueza. Hay confusores que no medimos, como el
ingreso, la lengua materna, la afiliación a un seguro de salud o la distancia a un servicio. Su
ausencia deja un margen de confusión residual: la altitud, el área y la región pueden estar
cargando con parte de ellos, y las asociaciones ajustadas lo son respecto de lo que sí medimos, no
de todo lo que importa.</p>

<h3>Una foto no tiene secuencia: la temporalidad</h3>
<p>Como la encuesta es una foto, la exposición y el evento se miden a la vez. Todas las
asociaciones de este boletín describen coexistencia, no secuencia, y esto vale para la altitud y
para cada uno de los factores {ref.par("mann2003")}. Los estudios de seguimiento muestran por qué
importa. En la violencia de pareja, la relación se ha observado en los dos sentidos
{ref.par("devries2013")}; lo mismo ocurre con la diabetes {ref.par("mezuk2008")}, la obesidad
{ref.par("luppino2010")} y el tabaco {ref.par("fluharty2017")}, y en el caso de la hipertensión se ha
descrito que la depresión antecede a la enfermedad {ref.par("meng2012")}. Además, la altitud que
usamos es la del lugar donde la persona vive hoy y no la de donde vivió antes, lo que deja sin
resolver el tiempo de exposición {ref.par("hernandez2022")}.</p>

<div class="nota">
  <strong>Para resumir.</strong> Estas cifras describen bien a los grupos y a la forma en que se
  relacionan los factores entre sí en 2025, y tienen límites reales para hablar de causas, de
  personas concretas y de lo que ocurre fuera de los hogares particulares.
</div>
</section>"""
    return plantilla("12-validez.html", "Sesgos y límites", contenido, "13")

# ─────────────────────────────────────────────────────────────────────
# 10 · El modelo
# ─────────────────────────────────────────────────────────────────────


def pagina_modelo() -> str:
    """La regresión logística explicada, con desempeño y mediación."""
    diag = tabla("tabla_24_diagnostico_logistica")
    med = tabla("tabla_43_efecto_total_vs_directo")

    contenido = f"""<section>
{cabecera("11", "trending-up", "El modelo")}
<p class="entradilla">Hasta aquí hemos mirado un factor a la vez. Un modelo los mira todos
juntos y responde otra pregunta: si dos personas se diferencian solo en una cosa, ¿cuánto
cambia eso?</p>

<h3>Qué es una regresión logística</h3>
<p>Imagina una balanza. Cada característica de una persona (su sexo, su edad, si tiene
hipertensión) pone un peso a un lado o al otro. La regresión logística es el procedimiento
que decide cuánto pesa cada cosa, mirando a la vez a las 28 553 personas del análisis.</p>

<p>Su resultado, el <strong>odds ratio</strong>, compara las <em>odds</em>, es decir, la razón
entre quienes dan positivo y quienes no. Un valor de 2 significa que esas odds se duplican; uno
de 0,5, que se reducen a la mitad; uno de 1, que no cambian. Y lo hace <em>manteniendo lo demás
constante</em>, que es justamente lo que no podíamos hacer comparando de a dos. Como la
sintomatología depresiva es poco frecuente (7 %), las odds y las prevalencias se parecen, y el
odds ratio se lee de forma aproximada como una razón de prevalencias; no es exacto y se aleja
cuando la condición es más frecuente {ref.par("barros2003")}.</p>

<h3>Asociación total y asociación directa</h3>
<p>Aquí aparece una decisión que es más conceptual que técnica. Si se supone que beber alcohol
lleva a la obesidad, y que la obesidad lleva a la depresión, ¿debemos descontar la obesidad al
medir la asociación del alcohol? Ese orden causal es un supuesto: la encuesta no puede
comprobarlo.</p>

<p>Depende de qué se quiera saber. Si preguntamos «¿cuánto se asocia beber, por todas las
vías?», la respuesta no debe descontarla: la ruta corporal es parte de la asociación. Si
preguntamos «¿cuánto se asocia beber por vías que no pasan por el cuerpo?», sí. Son dos
preguntas distintas, así que reportamos las dos.</p>

{figura(
    "fig_17_mediacion.png",
    "Descontar el peso corporal casi no cambia nada, y eso también es un resultado",
    "Cada fila es un factor medido dos veces. El círculo cuenta toda su asociación con la "
    "depresión y el cuadrado, solo la parte que no pasa por el peso corporal, de modo que la "
    "separación entre ambos es lo que viaja por esa ruta; si están pegados, el peso no hace de "
    "intermediario. En casi todos los casos lo están. La única excepción es la diabetes, donde "
    "alrededor de una cuarta parte de la asociación pasa por ahí, si se acepta el orden "
    "supuesto. La línea vertical del 1 separa lo que se asocia con más sintomatología de lo que "
    "se asocia con menos. Antes de calcular nada comprobamos el primer eslabón: de las cinco "
    "exposiciones, solo tres se asocian con la obesidad, y para las otras dos no hay ruta que "
    "descontar.",
    "Fuente: ENDES 2025 (INEI). Modelo A sin obesidad ni IMC; modelo B con ellos. La "
    "proporción mediada se calcula en la escala del logaritmo del odds ratio.",
    "Gráfico que compara dos estimaciones por exposición: el efecto total y el directo. Los "
    "pares de puntos casi coinciden salvo en la diabetes.")}

{html_tabla(med[["exposicion", "or_total_fmt", "or_directo_fmt", "lectura"]],
            {"exposicion": "Exposición", "or_total_fmt": "Asociación total",
             "or_directo_fmt": "Asociación directa", "lectura": "Lectura"},
            caption="Comparación entre el modelo A y el modelo B.")}

<h3>Qué tan bien funciona</h3>
{figura(
    "fig_12_roc_calibracion.png",
    "El modelo acierta dos de cada tres veces al comparar dos personas al azar",
    "Una curva ROC es como este juego: se toman dos personas al azar, una con sintomatología "
    "depresiva y otra sin ella, y se le pregunta al modelo cuál es cuál. Mientras más se "
    "despega la línea de la diagonal, mejor distingue, y un AUC de 0,67 quiere decir que "
    "acierta dos de cada tres veces: por encima del azar, que sería 0,5, y lejos de la "
    "certeza. El panel de la derecha mira otra cosa, la calibración: cuando el modelo dice "
    "«10 %», debería acertar alrededor del 10 % de las veces, y que los puntos sigan la "
    "diagonal significa que sus probabilidades son creíbles aunque no distinga con mucha "
    "finura. Con esa precisión se puede decidir dónde hace falta un servicio de salud mental; "
    "para saber cómo está una persona concreta hace falta hablar con ella.",
    "Fuente: ENDES 2025 (INEI). Curva ROC y calibración por deciles de riesgo sobre 28 553 "
    "personas.",
    "Dos paneles. A la izquierda, la curva ROC, que se aleja de la diagonal del azar. A la "
    "derecha, la curva de calibración, con los puntos cerca de la diagonal ideal.")}

{html_tabla(diag, {"aspecto": "Qué se evaluó", "valor": "Resultado",
                   "veredicto": "Interpretación"},
            caption="Diagnóstico completo del modelo logístico.")}

<div class="nota">
  <strong>Un AUC de 0,67 es lo que cabe esperar.</strong> Resultaría llamativo que un puñado de
  variables sociodemográficas predijera con precisión algo tan complejo como la depresión, y si el
  modelo diera 0,95, lo primero sería revisar que no se haya colado información del propio
  desenlace.
</div>
</section>"""
    return plantilla("10-modelo.html", "El modelo", contenido, "11")


# ─────────────────────────────────────────────────────────────────────
# 11 · SHAP frente a OR
# ─────────────────────────────────────────────────────────────────────


def pagina_shap() -> str:
    """El contraste entre importancia predictiva y magnitud del efecto."""
    comp = tabla("tabla_30_shap_vs_or")
    ml = tabla("tabla_28_comparacion_modelos_ml")

    contenido = f"""<section>
{cabecera("12", "search", "Modelo y realidad: dos rankings que no coinciden")}
<p class="entradilla">El factor con el efecto más fuerte del estudio apenas ayuda a
predecir quién dará positivo. Suena a contradicción y no lo es: son dos preguntas
distintas, y cada una tiene su propia respuesta.</p>

<p>Además del modelo epidemiológico entrenamos algoritmos de aprendizaje automático
(bosques aleatorios, XGBoost, LightGBM) y les preguntamos qué variables usan para decidir.
La técnica se llama SHAP y reparte la responsabilidad de cada predicción entre las
características de la persona.</p>

<p>Esperábamos que su ranking se pareciera al de los odds ratios. Coinciden en un 35 %.</p>

{figura(
    "fig_14_shap.png",
    "El consumo problemático de alcohol es el primero por efecto y el decimoquinto por utilidad predictiva",
    "Cada barra mide cuánto usa el modelo esa variable, en promedio, para decidir. No dice si "
    "la variable importa para la salud, sino si ayuda a adivinar, y por eso una variable puede "
    "tener un efecto grande y una barra pequeña si afecta a poca gente. El sexo domina el "
    "panel de la izquierda con el 37 % de la importancia, y el alcohol problemático apenas "
    "aparece, aunque su odds ratio es 6,07, el más alto del estudio. La explicación está en el "
    "denominador: afecta a 304 personas de 28 553, y un efecto enorme sobre muy poca gente casi "
    "no mueve la predicción media. El sexo es lo contrario: un efecto moderado sobre media "
    "población.",
    "Fuente: ENDES 2025 (INEI). Valores SHAP del mejor modelo de árboles, calculados sobre "
    "2 500 casos y precalculados para este boletín.",
    "Dos paneles. A la izquierda, barras horizontales con la importancia SHAP de cada "
    "variable; el sexo femenino encabeza con diferencia. A la derecha, la dispersión de los "
    "valores SHAP para esa variable.")}

{html_tabla(comp.head(10)[["etiqueta", "rango_or", "rango_shap", "or"]],
            {"etiqueta": "Variable", "rango_or": "Puesto por efecto",
             "rango_shap": "Puesto por utilidad predictiva", "or": "Odds ratio"},
            frozenset({"rango_or", "rango_shap", "or"}),
            "Los dos rankings, lado a lado. Cuanto mayor la diferencia, más informativa.")}

<h3>Por qué esto importa</h3>
<p>Porque llevan a decisiones distintas, y las dos tienen sentido.</p>

<ul>
  <li>Si la pregunta es <strong>«¿sobre qué conviene intervenir?»</strong>, manda la fuerza de
  la asociación, con la reserva de que solo habría impacto si fuera causal. La razón de
  prevalencias ajustada del consumo problemático de alcohol es 4,80; la fracción atribuible
  poblacional es de 2,2 %, porque lo declara el 1 % de la población (sección 10).</li>
  <li>Si la pregunta es <strong>«¿a quién priorizo con recursos limitados?»</strong>, manda
  la utilidad predictiva. Ahí el sexo, la edad y la región ordenan mejor a la población.</li>
</ul>

<p>Si se confunden, se puede errar en las dos direcciones: descartar una exposición relevante
porque no predice bien, o priorizar una intervención sobre una variable que solo predice
bien porque es frecuente.</p>

{figura(
    "fig_13_comparacion_modelos_ml.png",
    "Cuatro algoritmos, prácticamente el mismo resultado",
    "Cada curva es un algoritmo distinto, y mientras más se despega hacia la esquina superior "
    "izquierda, mejor distingue. La diagonal equivale a lanzar una moneda: las cuatro curvas "
    "quedan por encima, pero no muy lejos, entre 0,65 y 0,68. Se probaron cuatro maneras muy "
    "distintas de aprender de los mismos datos, desde una regresión clásica hasta tres "
    "algoritmos de los que se usan en competiciones, y cuando cambiar de método no mueve la "
    "aguja, el límite no está en el método sino en lo que la encuesta preguntó. El panel de la "
    "derecha es el más exigente cuando el fenómeno es poco frecuente: penaliza señalar a "
    "demasiada gente con tal de no perderse a nadie, así que mide si el modelo acierta al "
    "señalar y no solo si acierta al callar.",
    "Fuente: ENDES 2025 (INEI). Validación cruzada de cinco particiones, estratificada y "
    "agrupada por conglomerado muestral para evitar fuga de información.",
    "Dos paneles con curvas de rendimiento de cuatro modelos. Las curvas ROC de la izquierda "
    "están juntas y por encima de la diagonal; las de precisión-exhaustividad de la derecha "
    "también se solapan.")}

{html_tabla(ml[["modelo", "auc_roc", "auc_pr", "sensibilidad", "especificidad"]],
            {"modelo": "Modelo", "auc_roc": "AUC-ROC", "auc_pr": "AUC-PR",
             "sensibilidad": "Sensibilidad", "especificidad": "Especificidad"},
            frozenset({"auc_roc", "auc_pr", "sensibilidad", "especificidad"}),
            "Comparación de algoritmos. La última fila es la referencia obligada.")}

<div class="nota atencion">
  <strong>Por qué no aparece la exactitud.</strong> Un modelo que responda «nadie tiene
  depresión» a todo el mundo acierta el 94 % de las veces sin haber mirado a nadie. Como en la muestra del análisis
  apenas 6 de cada 100 personas dan positivo, ese número dice poco por sí solo: es una de las métricas más
  citadas, aunque en problemas como este es de las que menos informan.
</div>

<h3>Qué significa un AUC de 0,67, en cifras concretas</h3>

<p>Decir «discriminación moderada» suena a matiz técnico. Traducido, es esto:</p>

<div class="rejilla-cifras">
  <div class="cifra-tarjeta">
    <div class="cifra-grande">2 de cada 3</div>
    <p>Puestas dos personas al azar, una con síntomas y otra sin ellos, el modelo acierta
    cuál es cuál solo dos de cada tres veces. Eso <em>es</em> un AUC de 0,67.</p>
  </div>
  <div class="cifra-tarjeta">
    <div class="cifra-grande">85 de 100</div>
    <p>De cada cien personas que el modelo señala como riesgo, cerca de ochenta y cinco
    no dan positivo en el tamizaje. El valor predictivo positivo es 0,147.</p>
  </div>
  <div class="cifra-tarjeta">
    <div class="cifra-grande">2,2 %</div>
    <p>Es lo que mejora el error de calibración (Brier) frente a no tener modelo:
    0,0569 contra 0,0582. Una mejora real y muy pequeña.</p>
  </div>
  <div class="cifra-tarjeta">
    <div class="cifra-grande">4 de 4</div>
    <p>Cuatro familias de algoritmos, resultados entre 0,655 y 0,684. Cuando cambiar de
    método no cambia nada, el límite no está en el método.</p>
  </div>
</div>

<div class="nota">
  <strong>Un modelo moderado es coherente con lo que mide la encuesta.</strong>
  La depresión de una persona depende de su historia, sus duelos, su red de apoyo, su
  situación económica inmediata y su biología. Una encuesta de hogares mide sexo, edad,
  educación, dónde vive y unas pocas conductas. Con esas variables se puede describir
  <em>dónde se concentra</em> el problema en el país (y eso se hace bien, con intervalos
  estrechos y coherente con la literatura), aunque no permite saber quién lo tiene.
  <br><br>
  Un AUC de 0,90 con estas variables llamaría la atención más que alegrar: casi siempre indica
  que se coló una variable que ya contiene el desenlace. En este proyecto ese riesgo era real y
  concreto (<code>QS702</code> y <code>QS704A-I</code> se preguntan solo a quien ya marcó
  síntomas) y por eso se excluyeron desde el principio.
  <br><br>
  Preferimos reportar el techo tal como es. Un modelo con AUC 0,67 bien explicado orienta
  política pública sin prometer nada que no pueda cumplir. Presentado como «detector», en
  cambio, invitaría a usarlo sobre personas concretas, y ahí su aviso de riesgo no se confirma
  con frecuencia: cinco de cada seis veces.
</div>
</section>"""
    return plantilla("11-shap.html", "Modelo y realidad", contenido, "12")


# ─────────────────────────────────────────────────────────────────────
# 12 · Conclusiones
# ─────────────────────────────────────────────────────────────────────


def pagina_conclusiones() -> str:
    """Qué concluimos, qué no, y qué dicen los criterios de causalidad."""
    prev = tabla("tabla_08_prevalencias_ponderadas")
    nac = prev[prev.variable == "Total"].iloc[0]
    edu = prev[prev.variable == "Nivel educativo"].set_index("categoria")
    brecha = tabla("tabla_11_brecha_atencion").iloc[0]
    imp = tabla("tabla_58_riesgo_atribuible").set_index("variable")
    pasos = tabla("tabla_60_altitud_cruda_vs_ajustada").set_index("modelo")
    rp_alt = tabla("tabla_40_altitud_rp_ajustada").set_index("categoria")
    c4 = next(i for i in pasos.index if i.startswith("(4)") and "*" not in i)
    c6 = next(i for i in pasos.index if i.startswith("(6)") and "*" not in i)
    f4, f6 = pasos.loc[c4], pasos.loc[c6]
    alc, viol = imp.loc["alcohol_problematico"], imp.loc["violencia_fisica"]
    hta, dia = imp.loc["hta_dx"], imp.loc["diabetes_dx"]
    rp_2500 = rp_alt.loc["≥ 2 500 m"].rp_formato.split(" ")[0].replace(".", ",")

    criterios = pd.DataFrame([
        {"c": "Temporalidad",
         "h": "Exposición y síntomas se miden a la vez, en una sola foto.",
         "v": "Este diseño no permite evaluarlo, y es el límite que más pesa sobre todos los demás."},
        {"c": "Fuerza de la asociación",
         "h": f"Razón de prevalencias ajustada de {num(alc.rp_ajustada, 2)} para el consumo problemático "
              f"de alcohol y de {num(viol.rp_ajustada, 2)} para la violencia de pareja; de "
              f"{num(hta.rp_ajustada, 2)} y {num(dia.rp_ajustada, 2)} para la hipertensión y la diabetes.",
         "v": "Marcada en los dos primeros factores y moderada o discreta en el resto."},
        {"c": "Coherencia o consistencia",
         "h": f"El sentido de las asociaciones coincide con el de otro análisis peruano con una "
              f"encuesta nacional {ref.par('basauri2025')} y con revisiones internacionales por factor "
              f"(sección 10). En la altitud, la razón de prevalencias por encima de 2 500 m es "
              f"{rp_2500}, cercana al 1,41 de la ENDES de 2019 {ref.par('zegarra2022')}.",
         "v": "Favorable en la mayoría de los factores."},
        {"c": "Gradiente biológico (dosis-respuesta)",
         "h": f"La prevalencia baja de forma ordenada con el nivel educativo "
              f"({pc(edu.loc['Primaria o menos'].prevalencia)}, {pc(edu.loc['Secundaria'].prevalencia)} y "
              f"{pc(edu.loc['Superior'].prevalencia)}). Con la altitud la curva tiene forma de J y el "
              f"gradiente se atenúa dentro de un mismo departamento.",
         "v": "Presente para la educación; no concluyente para la altitud."},
        {"c": "Verosimilitud (plausibilidad)",
         "h": f"Hay mecanismos propuestos para varios factores, como el efecto del alcohol "
              f"{ref.par('boden2011')} o de la hipoxia crónica sobre la serotonina para la altitud "
              f"{ref.par('kious2018')}, que esta encuesta no puede contrastar.",
         "v": "Plausible para varios factores, sin verificar en nuestros datos."},
        {"c": "Reversibilidad",
         "h": "Pediría ver qué ocurre cuando desaparece la exposición, y no hay seguimiento.",
         "v": "Este diseño no permite evaluarlo."},
    ])

    contenido = f"""<section>
{cabecera("14", "shield-check", "Qué significa esto")}
<p class="entradilla">Seis conclusiones que los datos sostienen, y una lista igual de larga de cosas
que los datos no permiten afirmar. Las dos van juntas.</p>

<h3>Lo que muestran los datos</h3>

<p><strong>1. Una de cada catorce personas de 15 años o más presenta sintomatología depresiva
moderada o grave.</strong> Es el {pc(nac.prevalencia, 2)}, con un margen entre
{nac.ic_95.strip("()").replace(" – ", " y ").replace(".", ",")}. Es una estimación representativa de los hogares particulares del país, no de
quienes acuden a consulta.</p>

<p><strong>2. La brecha de atención es el hallazgo más grande.</strong> El {pc(brecha.brecha)} de
quienes dan positivo no vio a un profesional en un año, y la cifra no baja del 80 % en ningún grupo.
Es coherente con lo que se describe para el país, donde la gran mayoría de las personas con
trastornos mentales no accede a atención {ref.par("toyama2017")}. El cuello de botella parece estar
menos en detectar que en atender.</p>

<p><strong>3. La prevalencia se concentra donde ya se concentran otras desventajas.</strong> Es más
alta en las mujeres (una razón de prevalencias de 2,6), en quienes menos estudiaron, en los
extremos de la edad y en la sierra sur. El gradiente educativo sigue el patrón que se describe a
escala internacional {ref.par("lorant2003")}. Son cifras de grupo y describen territorios y
colectivos, no personas.</p>

<p><strong>4. La altitud se asocia con la depresión, con matices.</strong> Entre personas, el odds
ratio por cada 1 000 m es de {num(f4.or_por_1000m)} (IC 95 % {num(f4.ic_inf)} a {num(f4.ic_sup)}) al
ajustar por lo que medimos, en el mismo sentido y con una magnitud del mismo orden que en otros
análisis peruanos {ref.par("hernandez2022", "zegarra2022")}. La asociación se atenúa a
{num(f6.or_por_1000m)} (IC 95 % {num(f6.ic_inf)} a {num(f6.ic_sup)}) al comparar dentro de un mismo
departamento, y la altitud no confunde a ninguno de los demás factores. Es una asociación con
gradiente, en parte explicable por el contexto andino, y una pregunta abierta bien planteada.</p>

<p><strong>5. Ajustar cambia las conclusiones, a veces de signo.</strong> Fumar parecía protector y no
lo es. Es un buen recordatorio de que una comparación sin ajustar entre dos grupos rara vez responde la
pregunta que uno cree estar haciendo.</p>

<p><strong>6. Fuerza y alcance no son lo mismo.</strong> El consumo problemático de alcohol tiene la
asociación más fuerte ({num(alc.rp_ajustada, 2)}) y una fracción atribuible poblacional de
{pc(alc.paf_ajustada)}, porque lo declara una persona de cada cien. La violencia de pareja
({pc(viol.paf_ajustada)}, entre quienes tuvieron pareja) y la hipertensión ({pc(hta.paf_ajustada)})
alcanzan a más casos con una asociación menos intensa.</p>

<h3>Qué dicen los criterios de causalidad</h3>
<p>Para ordenar qué tan cerca estamos de poder hablar de causas, repasamos los criterios clásicos
{ref.par("hill1965")} frente a lo que encontramos. El resultado es una lectura equilibrada: hay
argumentos a favor, y hay uno, el más importante, que este diseño no puede aportar.</p>

{html_tabla(criterios, {"c": "Criterio", "h": "Lo que vemos en nuestros datos", "v": "Cómo lo leemos"},
            caption="Los criterios de causalidad aplicados a nuestros hallazgos.")}

<h3>Lo que estos datos no permiten afirmar</h3>

<div class="nota">
  <strong>Los datos no permiten hablar de causas ni de secuencia.</strong> El estudio mide la exposición y el
  resultado en el mismo momento, así que no sabemos qué vino antes. Puede que beber en exceso
  contribuya a la depresión, que la depresión lleve a beber, o que un tercer factor produzca las
  dos cosas. Vale para la altitud y para todos los factores.
</div>

<div class="nota">
  <strong>No estamos midiendo depresión diagnosticada.</strong> El PHQ-9 es un tamizaje que
  responde la propia persona. Habrá quien puntúe alto sin tener un trastorno depresivo, y quien lo
  tenga sin puntuar alto.
</div>

<div class="nota">
  <strong>El punto de corte no está validado en el Perú.</strong> Usamos 10 porque es el que mejor
  funciona en estudios internacionales. La versión peruana tuvo una validación de expertos y una
  comprobación de su estructura, pero no conocemos un estudio de criterio que fije el umbral
  local. Si el umbral óptimo aquí fuera distinto, la prevalencia también.
</div>

<div class="nota">
  <strong>Faltan quienes no respondieron y quienes no viven en hogares particulares.</strong>
  Quedó fuera el 9,4 % que no completó el PHQ-9 y quienes están fuera del universo de la encuesta.
  Con lo que sabemos no es posible decir si eso sube o baja la prevalencia. Quedaron fuera también
  de los modelos las personas que nunca asistieron a la escuela, un grupo con prevalencia más alta,
  aunque incluirlas no cambió los resultados principales.
</div>

<div class="nota">
  <strong>Los mapas describen territorios, no personas.</strong> Que un departamento tenga más
  prevalencia no dice que cada persona de allí la tenga. Y la región natural es una aproximación:
  la derivamos de la altitud del conglomerado y no de la clasificación oficial por distrito.
</div>

<div class="nota">
  <strong>Quedan confusores sin medir.</strong> No contamos con ingreso, lengua materna, seguro de
  salud ni distancia a un servicio, de modo que las asociaciones ajustadas pueden seguir cargando
  con parte de ellos.
</div>

<h3>Qué haríamos con esto</h3>
<p>Si estos resultados tuvieran que traducirse en decisiones, apuntarían a tres cosas:</p>

<ul>
  <li><strong>Priorizar territorialmente.</strong> La sierra sur acumula más prevalencia y más
  brecha de atención, con la salvedad de que son cifras de departamentos. Sirven para decidir por
  dónde empezar, y no para describir a cada persona que vive allí.</li>
  <li><strong>Tamizar donde la gente ya está.</strong> Si casi nueve de cada diez personas con
  tamizaje positivo no llegan a un servicio de salud mental, una opción razonable es ofrecer la
  evaluación en los servicios que sí frecuentan, como el primer nivel de atención.</li>
  <li><strong>Estudiar la altura con un diseño a la medida.</strong> La señal coincide con la de la
  ENDES de 2019 por encima de los 2 500 m, pero se atenúa al comparar dentro de un departamento, y
  una encuesta transversal no puede separarla de la pobreza ni del acceso a servicios. Haría falta
  un estudio con seguimiento y con medidas del tiempo de residencia.</li>
</ul>

<div class="dos-columnas">
  <div>
    <h3>Sobre la reproducibilidad</h3>
    <p>Todo lo que hay en este boletín se regenera con un comando desde los microdatos públicos del
    INEI. Las tablas, las figuras, los mapas y este mismo texto salen del mismo proceso. Cualquiera
    puede descargar el código, ejecutarlo y obtener las mismas cifras, o encontrar dónde nos
    equivocamos, y lo agradeceremos.</p>
  </div>
  <div>
    <img class="ilustracion" src="{IMG}/ilustraciones/comunidad.svg"
         alt="Ilustración de un grupo de personas de distintas edades">
    <p class="credito-img">Ilustración original del proyecto</p>
  </div>
</div>
</section>"""
    return plantilla("13-conclusiones.html", "Conclusiones", contenido, "14")


# ─────────────────────────────────────────────────────────────────────
# 13 · Cierre
# ─────────────────────────────────────────────────────────────────────


def pagina_cierre() -> str:
    """Recursos de ayuda verificados, enlaces y referencias."""
    catalogo = json.loads(
        (cfg.RAIZ / "agente" / "recursos_ayuda.json").read_text(encoding="utf-8"))
    verificado = catalogo["_verificado_el"]

    tarjetas = ""
    for r in catalogo["recursos"]:
        numero = f'<div class="numero">{r["telefono"]}</div>' if r.get("telefono") else ""
        meta = []
        if r.get("gratuito"):
            meta.append("Gratuito")
        if r.get("horario"):
            meta.append(r["horario"])
        tarjetas += f"""<div class="recurso">
  {numero}
  <h4>{r['nombre']}</h4>
  <p>{r['descripcion']}</p>
  <p class="meta">{' · '.join(meta)}</p>
</div>"""

    enlaces = pd.DataFrame([
        {"q": "Código y datos", "d": f'<a href="{REPO}">{REPO}</a>'},
        {"q": "Este boletín en línea", "d": f'<a href="{PAGES}">{PAGES}</a>'},
        {"q": "Simulador interactivo", "d": f'<a href="{WEB}">{WEB}</a>'},
        {"q": "Fuente de los microdatos",
         "d": '<a href="https://proyectos.inei.gob.pe/microdatos/">Microdatos del INEI</a> · '
              "ENDES 2025, módulos CSALUD01 y RECH0"},
        {"q": "Referencias en BibTeX",
         "d": f'<a href="{REPO}/blob/main/docs/referencias.bib">docs/referencias.bib</a>'},
        {"q": "Límites geográficos",
         "d": "INEI 2023, distribuidos por geogpsperu / SuyoPomalia"},
        {"q": "Licencia", "d": "MIT · el análisis puede reutilizarse citando la fuente"},
    ])

    contenido = f"""<section>
{cabecera("15", "phone-call", "Si necesitas ayuda")}
<p class="entradilla">Estos números son gratuitos, funcionan en todo el país y atienden
personas, no casos. Están verificados contra las fuentes oficiales el {verificado}.</p>

<div class="cierre-animo">
  <p class="cierre-titulo">Si has llegado hasta aquí buscándote en los datos</p>
  <p>Puede que hayas abierto este boletín por curiosidad. Puede también que lo hayas
  abierto porque llevas un tiempo sintiéndote mal. Si es lo segundo, hay algo que estas
  mismas cifras dicen y conviene leer despacio: <strong>casi siete de cada cien personas
  en el Perú dieron positivo en este tamizaje</strong>. Son cientos de miles. No es un
  fallo de carácter ni algo que le pase a poca gente.</p>
  <p>Tampoco es algo que se arregle poniéndole ganas. Es un problema de salud y, como
  cualquier otro, tiene quien lo trate. Los servicios de abajo son gratuitos y no hace
  falta que nadie te derive.</p>
  <p>Para quien llegó hasta aquí, una frase para llevarse:</p>
  <blockquote class="frase-animo" id="frase-cierre">
    <p>Hay algo bueno en este mundo, señor Frodo. Y vale la pena luchar por ello.</p>
    <cite>Samsagaz Gamyi · El Señor de los Anillos: las dos torres (2002)</cite>
  </blockquote>
</div>

<div class="recursos">{tarjetas}</div>

<div class="aviso-legal">
  <strong>Este boletín no diagnostica.</strong> Todo lo que contiene son estimaciones
  epidemiológicas de riesgo poblacional, con fines académicos y de salud pública. No
  constituye un diagnóstico médico ni reemplaza la evaluación de un profesional de salud
  mental. Si algo de lo que leíste te resuena, hablar con un profesional es el paso que sí
  puede evaluar tu situación.
</div>

<div class="dos-columnas invertida">
  <div>
    <img class="ilustracion" src="{IMG}/ilustraciones/apoyo.svg"
         alt="Ilustración de una persona acompañando a otra">
    <p class="credito-img">Ilustración original del proyecto</p>
  </div>
  <div>
    <h3>Cómo encontrar un centro cerca</h3>
    <p>Los <strong>Centros de Salud Mental Comunitaria</strong> son la puerta de entrada al
    tratamiento en el sistema público: atienden por psicología, psiquiatría y trabajo social,
    de forma gratuita. Puedes preguntar por el más cercano en cualquier establecimiento de
    salud de tu distrito, o llamando a la Línea 113.</p>
    <p>La red no cubre el país de forma pareja, y eso es parte de lo que muestra este
    boletín. Aun así, preguntar cuesta una llamada.</p>
  </div>
</div>

<h3>El proyecto</h3>
{html_tabla(enlaces, {"q": "Recurso", "d": "Enlace"})}

<h3>Referencias</h3>
<p>Cada referencia se abrió y se comprobó contra su fuente antes de citarla. La misma lista, en
formato BibTeX, está en el repositorio.</p>
{ref.lista_html()}

<p class="ficha" style="margin-top:32px">
  Boletín elaborado en agosto de 2026 y revisado en noviembre de 2026 para el curso de
  Epidemiología 2026-2 de la Escuela Profesional de Estadística, Facultad de Ciencias
  Matemáticas, Universidad Nacional Mayor de San Marcos.
</p>
</section>"""
    # Una frase distinta en cada visita, tomada del banco cerrado del proyecto. Sin JavaScript
    # queda la de Samsagaz, que está verificada. Las «Inspirado en» son adaptaciones y así se leen.
    banco = json.loads((cfg.RAIZ / "contenido" / "frases_animo.json").read_text(encoding="utf-8"))
    frases = [{"texto": f["texto"], "fuente": f["fuente"]} for f in banco["frases"]]
    datos = json.dumps(frases, ensure_ascii=False, separators=(",", ":")).replace("</", "<\/")
    script = """<script>
(function () {
  var F = %FRASES%;
  var caja = document.getElementById('frase-cierre');
  if (!caja || !F.length) return;
  var f = F[Math.floor(Math.random() * F.length)];
  caja.querySelector('p').textContent = f.texto;
  caja.querySelector('cite').textContent = f.fuente;
})();
</script>""".replace("%FRASES%", datos)
    return plantilla("14-cierre.html", "Ayuda y cierre", contenido + script, "15")


# ─────────────────────────────────────────────────────────────────────
# Orquestador
# ─────────────────────────────────────────────────────────────────────


def main() -> None:
    """Genera las quince páginas del boletín y el .bib con las referencias citadas."""
    SALIDA.mkdir(parents=True, exist_ok=True)
    ref.reiniciar()
    destino_img = SALIDA / "assets" / "img"
    destino_img.mkdir(parents=True, exist_ok=True)
    for origen in list(cfg.FIGURAS.glob("*.png")) + list(cfg.MAPAS.glob("mapa_*.png")):
        shutil.copy(origen, destino_img / origen.name)

    paginas = {
        "index.html": pagina_caratula(),
        "01-que-es.html": pagina_que_es(),
        "02-problematica.html": pagina_problematica(),
        "03-deteccion.html": pagina_deteccion(),
        "04-datos.html": pagina_datos(),
        "05-medicion.html": pagina_medicion(),
        "06-quienes.html": pagina_quienes(),
        "07-geografia.html": pagina_geografia(),
        "08-factores.html": pagina_factores(),
        "09-asociacion.html": pagina_asociacion(),
        "10-modelo.html": pagina_modelo(),
        "11-shap.html": pagina_shap(),
        "12-validez.html": pagina_validez(),
        "13-conclusiones.html": pagina_conclusiones(),
        "14-cierre.html": pagina_cierre(),
    }
    # Páginas de versiones anteriores: con la numeración nueva dejarían enlaces
    # a contenido desfasado.
    for viejo in ("descriptivo.html", "factores.html", "modelo.html", "metodologia.html",
                  "09-modelo.html", "10-shap.html", "11-conclusiones.html", "12-cierre.html",
                  "10-validez.html", "11-modelo.html", "12-shap.html"):
        (SALIDA / viejo).unlink(missing_ok=True)

    for nombre, html in paginas.items():
        (SALIDA / nombre).write_text(html, encoding="utf-8")
        print(f"  {nombre:24s} {len(html) / 1024:6.1f} KB")

    # El .bib sale de las mismas citas que la lista del boletín, así que son
    # consistentes por construcción. La lista se escribe al armar el cierre, que
    # es la última página en generarse.
    (cfg.DOCS / "referencias.bib").write_text(ref.bib_citadas(), encoding="utf-8")
    print(f"  referencias.bib        {len(ref._citadas)} referencias citadas")
    print(f"\n{len(paginas)} páginas generadas en {SALIDA}")
    print("Para verlo:  python -m http.server 8000 --directory boletin")


if __name__ == "__main__":
    main()
