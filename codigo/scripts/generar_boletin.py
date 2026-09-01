"""Fase 3 · Boletín epidemiológico de trece secciones.

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

3. **Los gráficos técnicos llevan su clave de lectura.** Nadie fuera de la
   carrera sabe leer un forest plot ni una curva de calibración, y presentarlos
   sin instrucciones es escribir para uno mismo.

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
    ("09-modelo.html", "El modelo", "10"),
    ("10-shap.html", "Modelo y realidad", "11"),
    ("11-conclusiones.html", "Qué significa", "12"),
    ("12-cierre.html", "Ayuda y cierre", "13"),
]

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


def figura(archivo: str, titulo: str, explicacion: str, ficha: str,
           alt: str, como_leer: list[str] | None = None) -> str:
    """Bloque de gráfico: título que afirma, explicación, imagen y ficha técnica."""
    clave = ""
    if como_leer:
        puntos = "".join(f"<li>{p}</li>" for p in como_leer)
        clave = ('<div class="como-leer"><strong>Cómo leer este gráfico</strong>'
                 f"<ul>{puntos}</ul></div>")
    return f"""<figure class="figura">
  <p class="titulo-hallazgo">{titulo}</p>
  <p class="explicacion">{explicacion}</p>
  {clave}
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
    Línea 113, opción 5 — salud mental<br>
    Gratuita, 24 horas, MINSA<br>
    <a href="12-cierre.html">Todos los recursos</a>
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


def plantilla(archivo: str, titulo: str, contenido: str, numero: str | None = None) -> str:
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
    etiqueta_num = f'<span class="num">{numero} de 13</span>' if numero else ""

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
  <span class="seccion-num">Sección {numero} de 13</span>
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
        {"s": "7 – 11", "q": "Resultados",
         "d": "Quiénes son, dónde están, qué se asocia, qué dice el modelo y en qué se contradice"},
        {"s": "12 – 13", "q": "Cierre",
         "d": "Qué concluimos, qué no podemos concluir y dónde pedir ayuda"},
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
    <p class="entradilla">Sobre 30 226 personas entrevistadas en todo el país, estimado con
    el diseño muestral complejo de la encuesta, que es lo que corresponde cuando la gente
    se entrevista por conglomerados y no de una en una.</p>
    <div class="kpis">
      <div class="kpi">
        <div class="valor">{nac.prevalencia:.2f} %</div>
        <div class="nombre">Prevalencia nacional</div>
        <div class="detalle">PHQ-9 ≥ 10 · IC 95 % {nac.ic_95}</div>
      </div>
      <div class="kpi atencion">
        <div class="valor">{brecha.brecha:.1f} %</div>
        <div class="nombre">No recibió atención</div>
        <div class="detalle">De quienes dan positivo al tamizaje</div>
      </div>
      <div class="kpi">
        <div class="valor">1 de 14</div>
        <div class="nombre">Personas afectadas</div>
        <div class="detalle">Entre quienes tienen 15 años o más</div>
      </div>
      <div class="kpi">
        <div class="valor">11,6×</div>
        <div class="nombre">Diferencia entre extremos</div>
        <div class="detalle">Puno frente a Ucayali</div>
      </div>
    </div>

    <h3>Cómo está organizado</h3>
    <p>Las cuatro primeras secciones explican de qué hablamos y por qué importa. A partir
    de la quinta el tono cambia: entran los datos, el método y los resultados. La última
    reúne los recursos de ayuda.</p>

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
<p class="entradilla">No es tristeza. La tristeza va y viene, tiene un motivo y se
disuelve sola. La depresión se queda, no siempre necesita un motivo y no se disuelve por
voluntad propia.</p>

<div class="dos-columnas">
  <div>
    <p>La Organización Mundial de la Salud la define como un trastorno mental frecuente,
    caracterizado por tristeza persistente y pérdida de interés en actividades que antes
    resultaban placenteras, junto con dificultad para llevar adelante la vida cotidiana
    durante al menos dos semanas.</p>

    <p>La palabra clave es <strong>persistente</strong>. Alguien puede pasar un mal día,
    una mala semana, un duelo. Eso es parte de estar vivo. Lo que distingue a la depresión
    es que el estado se instala y empieza a interferir con dormir, comer, trabajar,
    estudiar y relacionarse.</p>

    <p>Tampoco es cuestión de carácter ni de falta de voluntad. Es un problema de salud
    con causas biológicas, psicológicas y sociales entrelazadas, y con tratamientos que
    funcionan.</p>
  </div>
  <div>
    <img class="ilustracion" src="{IMG}/ilustraciones/conversacion.svg"
         alt="Ilustración de dos personas conversando, una escuchando a la otra">
    <p class="credito-img">Ilustración original del proyecto</p>
  </div>
</div>

<h3>Cómo se manifiesta</h3>
<p>No se ve igual en todo el mundo. Hay quien lo vive como tristeza y hay quien lo vive
como cansancio, insomnio o dolores sin causa aparente. En los datos de este boletín, los
síntomas más frecuentes no son los que uno esperaría:</p>

{html_tabla(top[["sintoma", "pct_positivo", "pct_relevante"]],
            {"sintoma": "Síntoma", "pct_positivo": "Lo reportó al menos un día (%)",
             "pct_relevante": "La mayoría de días (%)"},
            frozenset({"pct_positivo", "pct_relevante"}),
            "Los tres síntomas más reportados en la ENDES 2025, sobre 30 401 personas.")}

<p>El sueño y el ánimo encabezan la lista. Alguien que duerme mal y anda sin energía puede
no reconocerse en la palabra «depresión» y estar atravesándola igualmente.</p>

<div class="nota atencion">
  <strong>Una precisión importante.</strong> A lo largo de este boletín hablamos de
  «sintomatología depresiva» y no de «depresión diagnosticada». El instrumento que usa la
  encuesta es un cuestionario de tamizaje: identifica a quien probablemente necesita una
  evaluación, no reemplaza el diagnóstico de un profesional.
</div>

<h3>Cuánto pesa en el mundo</h3>
<p>La OMS estima que los trastornos depresivos afectan a cientos de millones de personas y
figuran entre las principales causas de discapacidad a nivel global. Su peso no está en la
mortalidad directa sino en los años vividos con limitación: estudios interrumpidos,
trabajos que no se sostienen, vínculos que se erosionan.</p>
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
    <div class="valor">{nac.prevalencia:.2f} %</div>
    <div class="nombre">Presenta sintomatología depresiva</div>
    <div class="detalle">Moderada o grave, PHQ-9 ≥ 10</div>
  </div>
  <div class="kpi atencion">
    <div class="valor">{nacional:.1f} %</div>
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

    <p>Eso descarta la explicación fácil. El problema no está en un grupo concreto: el
    sistema no está llegando a casi nadie.</p>
  </div>
</div>

<h3>Por qué la gente no llega</h3>
<p>La encuesta no pregunta por los motivos, así que aquí solo podemos señalar lo que la
literatura y la propia estructura del sistema hacen plausible:</p>

<ul>
  <li><strong>No reconocerlo como un problema de salud.</strong> Si el malestar se vive
  como cansancio o como carácter, no lleva a nadie a un consultorio.</li>
  <li><strong>Estigma.</strong> Pedir ayuda en salud mental sigue costando más que pedirla
  para cualquier otra dolencia.</li>
  <li><strong>Disponibilidad desigual.</strong> Los servicios especializados se concentran
  en las ciudades grandes, no en los departamentos donde la prevalencia es más alta.</li>
  <li><strong>Costo y tiempo.</strong> Llegar a una consulta puede significar un día de
  viaje y un día de trabajo perdido.</li>
</ul>

<div class="nota">
  <strong>Lo que sí se puede afirmar con estos datos.</strong> Que el problema de la
  depresión en el Perú, medido con esta encuesta, es tanto de prevalencia como de atención.
  Y que la segunda parte es la más grande de las dos.
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
<p class="entradilla">Detectar a tiempo no es un tecnicismo de salud pública. Es la
diferencia entre unos meses difíciles y unos años perdidos.</p>

<div class="dos-columnas">
  <div>
    <p>Un episodio depresivo que se identifica pronto suele responder mejor y dejar menos
    huella. Uno que se arrastra durante años tiende a volverse más difícil de tratar, a
    dejar secuelas en el trabajo y en los vínculos, y a acompañarse de otras condiciones de
    salud.</p>

    <p>El problema es que la depresión no manda un aviso. No hay fiebre ni prueba de
    laboratorio. Quien la atraviesa muchas veces no la nombra, y quien lo rodea la
    interpreta como desgana.</p>

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
  atención. No puede decir qué le va a pasar a nadie en concreto, ni qué causa qué: los
  datos vienen de una foto tomada en un momento, no de un seguimiento en el tiempo.
</div>

<h3>El instrumento: el PHQ-9</h3>
<p>Nueve preguntas sobre cómo se ha sentido la persona en las dos últimas semanas. Cada
respuesta puntúa de 0 a 3 según cuántos días apareció el síntoma, y la suma va de 0 a 27.
A partir de 10 se considera que hay sintomatología moderada o grave y que conviene una
evaluación profesional.</p>

<p>Es breve, está validado internacionalmente y se puede aplicar en una encuesta de hogares
sin necesidad de un especialista. Eso es lo que lo hace útil a escala de país — y también
lo que marca su límite: no reemplaza a nadie.</p>
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
<p>La <strong>Encuesta Demográfica y de Salud Familiar</strong> es el operativo estadístico
más grande que el INEI dedica a la salud de los hogares peruanos. Se levanta todos los años,
recorre los 25 departamentos y pregunta por salud reproductiva, nutrición, enfermedades
crónicas y, en el módulo que usamos aquí, salud mental.</p>

<p>Para este boletín usamos la ola de 2025: el cuestionario de salud aplicado a una persona
de 15 años a más seleccionada en cada hogar, cruzado con el registro del hogar, que aporta
la ubicación y las variables del diseño muestral.</p>

<h3>Por qué no es una encuesta cualquiera</h3>
<p>La ENDES no elige a la gente al azar de una lista nacional. Divide el país en estratos,
sortea conglomerados dentro de cada estrato y visita viviendas dentro de cada conglomerado.
Eso abarata el operativo, pero tiene una consecuencia estadística: las personas de un mismo
conglomerado se parecen entre sí, y tratarlas como independientes daría intervalos de
confianza demasiado estrechos.</p>

{html_tabla(ficha, {"elemento": "Elemento del diseño", "valor": "Valor"},
            caption="Ficha del diseño muestral tal como se declaró en el análisis.")}

<div class="nota">
  <strong>Qué significa el efecto de diseño.</strong> Un valor de 3,09 quiere decir que
  estas 30 226 entrevistas aportan tanta información como unas 9 774 tomadas completamente
  al azar. Es el precio de recorrer un país entero, no un defecto de la encuesta.
  Lo que sí sería un error es ignorarlo al calcular los intervalos.
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
    "Nueve de cada cien entrevistas no completaron el cuestionario de salud mental, casi "
    "siempre porque la persona no estaba, rechazó responder o dejó la entrevista a medias. "
    "Otras 175 no traían el factor de ponderación necesario para estimar. Cada exclusión "
    "está contada, porque una muestra que se encoge sin explicación es una muestra en la "
    "que no se puede confiar.",
    "Fuente: ENDES 2025 (INEI). Elaboración propia siguiendo la guía STROBE.",
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
         "d": "Metros sobre el nivel del mar del conglomerado donde vive, dato del propio "
              "marco muestral",
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
            "conjunto es alta: alfa de Cronbach de 0,875.")}

<div class="nota atencion">
  <strong>Sobre el noveno ítem.</strong> Pregunta por pensamientos de hacerse daño. Entra
  en el puntaje porque forma parte del instrumento, pero no lo analizamos ni lo destacamos
  por separado en ningún punto de este boletín. Publicar un porcentaje de ideación suicida
  como titular, sin el acompañamiento que un estudio observacional no puede ofrecer, sería
  irresponsable.
</div>

<h3>El punto de corte</h3>
<p>Usamos 10, que es el umbral convencional para «caso probable» de depresión moderada o
grave. Como análisis de sensibilidad repetimos todo con el corte en 5, que capta también la
sintomatología leve y sube la prevalencia al 21,4 %. Las conclusiones no cambian.</p>

<h3>Cómo entra la edad en el modelo</h3>

<p>Una prueba estándar dice que la edad <strong>no se relaciona con la depresión en línea
recta</strong>: la prevalencia es alta entre los más jóvenes, cae hacia los treinta y vuelve
a subir después. Metida como una recta, ese doble movimiento se anula y la edad parece no
importar.</p>

<p>Hay dos formas razonables de resolverlo: partirla en <strong>grupos</strong> (15-19,
20-29, y así) o dejar que una curva flexible —una <em>spline</em>— se ajuste sola a la forma
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
  <strong>La curva ajusta mejor, y aun así usamos los grupos. El motivo importa.</strong>
  Lo que decide qué forma usar no es cuál ajusta mejor la edad, sino si esa elección
  <em>distorsiona el resto del modelo</em>. Y no lo hace: al cambiar de una a otra, el
  coeficiente que más se mueve lo hace un <strong>4,3 %</strong>, muy por debajo del 10 %
  que se toma como señal de que una variable está confundiendo a las demás.
  <br><br>
  Con eso resuelto, la elección deja de ser de validez y pasa a ser de comunicación. Los
  grupos de edad dan cifras que se leen solas —«el grupo de 60+ frente al de 30-39»—, son la
  forma en que reportan los estudios con los que nos comparamos, y una curva flexible
  necesita un gráfico para interpretarse. La curva queda documentada como comprobación, y
  cualquiera puede reproducirla con el código.
</div>

<h3>Qué pasa con quien no contestó todo</h3>
<p>El análisis principal usa solo a quienes tienen completas las variables del modelo. Eso
deja fuera a poca gente —el faltante más grande es el nivel educativo, con un 3,8 %— pero
conviene comprobar que esa exclusión no está inclinando el resultado.</p>

<p>Se repitió el modelo rellenando los huecos con <strong>imputación múltiple</strong>:
cinco versiones del conjunto de datos, cada una con un valor plausible distinto en los
huecos, y los resultados combinados. De los diecisiete coeficientes, dieciséis se mueven
menos de un 8 %. El único que cambia de forma apreciable es la diabetes, que pasa de 1,33
a 1,49 —un 10,5 %— y se acerca al resto de enfermedades crónicas en vez de alejarse.</p>

<p>Ninguna conclusión del boletín depende de esa diferencia, pero queda dicho: quien
prefiera la versión con imputación leerá una asociación algo más fuerte entre diabetes y
sintomatología depresiva, no una distinta.</p>

<p><strong>Una limitación honesta:</strong> el corte de 10 viene de estudios de validación
internacionales. No conocemos una validación del PHQ-9 en población peruana que proponga un
umbral propio. Si ese umbral óptimo local fuera distinto, la prevalencia que reportamos
cambiaría.</p>

<h3>Las demás variables</h3>
{html_tabla(variables, {"v": "Variable", "d": "Definición operativa", "c": "En la muestra"},
            caption="Definición exacta de cada variable usada en el análisis.")}

<div class="nota">
  <strong>Tres variables que quedaron fuera a propósito.</strong> La encuesta incluye una
  pregunta sobre cuánto dificultan los síntomas la vida diaria, y una segunda batería PHQ-9
  referida a doce meses. Las dos parecen predictores excelentes, y ahí está el problema:
  solo se le preguntan a quien ya declaró síntomas. Miden lo mismo que queremos explicar,
  así que no aportan información nueva — la cobertura de esas preguntas <em>es</em> el
  resultado, disfrazado. Un modelo que las incluyera acertaría casi siempre y no habría
  aprendido nada.
</div>
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
grupos más que en otros, y el patrón dice bastante sobre el país.</p>

{figura(
    "fig_02_prevalencia_subgrupos.png",
    "Las mujeres presentan sintomatología depresiva dos veces y media más que los hombres",
    "9,87 % frente a 3,86 %. Es la brecha más grande de todo el boletín, mayor que la que "
    "separa a la sierra de la selva o a quien terminó la primaria de quien terminó la "
    "universidad. Aparece en todos los grupos de edad y en todas las regiones, así que no "
    "se explica por ninguna de esas otras diferencias.",
    "Fuente: ENDES 2025 (INEI). Prevalencias ponderadas con el diseño muestral complejo. "
    "Las barras horizontales son intervalos de confianza al 95 %. n = 30 226.",
    "Gráfico de barras horizontales con la prevalencia de depresión por sexo, grupo etario, "
    "nivel educativo, área de residencia y región natural. La barra más larga corresponde a "
    "las mujeres, con casi 10 %, y la más corta a los hombres, con menos de 4 %.")}

{figura(
    "fig_01_distribucion_phq9.png",
    "La mitad de las personas responde cero en las nueve preguntas",
    "Ese pico en el extremo izquierdo no es un error: más de quince mil personas no "
    "reportaron ningún síntoma en dos semanas. La otra mitad se reparte en una cola que se "
    "adelgaza rápido. Esta forma —muchísimos ceros y unos pocos valores altos— es la razón "
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
primaria, 7,05 % en secundaria y 5,28 % en educación superior. La diferencia sobrevive al
ajuste por edad y sexo, así que no es solo que las personas mayores hayan estudiado
menos.</p>

{figura(
    "fig_03_items_phq9.png",
    "Dormir mal y sentirse decaído son los síntomas que más aparecen",
    "Cada barra reparte a la población entre quienes no sintieron nada, quienes lo "
    "sintieron algunos días y quienes lo sintieron casi a diario. Los problemas de sueño "
    "encabezan la lista, por delante del ánimo deprimido. Tiene una consecuencia práctica: "
    "quien consulta por insomnio puede estar consultando por depresión sin saberlo.",
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
junto a la del país y la de los departamentos que tiene más cerca en la escala.</p>

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
        + coma(r, 1) + ' veces la cifra nacional.');
    } else if (r <= 0.87) {
      partes.push('<strong>' + d.nombre + '</strong> está por debajo del promedio del país. '
        + 'En el conjunto del Perú la proporción es ' + coma(1 / r, 1) + ' veces la de aquí.');
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
      + '<tr><th>Altitud media</th><td>' + d.altitud_media.toLocaleString('es-PE').replace(/,/g, ' ')
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
    mod_alt = tabla("tabla_38_altitud_modelos")

    estimables = int(prov.estimable.sum())
    ajustado = mod_alt[mod_alt.modelo.str.startswith("(b)")].iloc[0]

    contenido = f"""<section>
{cabecera("8", "map-pin", "Dónde está la depresión")}
<p class="entradilla">Puno tiene once veces la prevalencia de Ucayali. No es un matiz
regional: es otro país dentro del mismo país.</p>

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

<h3>Hasta dónde se puede bajar</h3>
{figura(
    "mapa_02_provincial.png",
    f"Solo {estimables} de las 196 provincias tienen muestra suficiente para estimar",
    "Bajar de departamento a provincia es tentador y casi siempre es un error. La encuesta "
    "está diseñada para dar cifras departamentales; al partirla en 196 pedazos, más de la "
    "cuarta parte se queda con menos de cincuenta personas. Esas provincias van tramadas, "
    "no coloreadas. Un mapa da a cada polígono la misma autoridad visual, y pintar una "
    "provincia estimada con doce casos junto a Lima con cuatro mil sería mentir sin decir "
    "una sola cifra falsa.",
    f"Fuente: ENDES 2025 (INEI). Umbral mínimo de 50 personas por provincia. {estimables} "
    f"provincias estimables; la mediana de las descartadas tiene 28 personas.",
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

<h3>La altura</h3>
<p>El contraste entre Puno y Ucayali —altiplano contra selva baja— sugiere una pregunta que
la literatura internacional ya se hizo: ¿tiene algo que ver la altitud? Hay estudios sobre
hipoxia crónica y trastornos del ánimo, y hay un antecedente peruano directo con la ENDES
de 2019.</p>

{figura(
    "fig_15_altitud.png",
    "Por encima de los 2 000 metros la prevalencia empieza a subir, y no antes",
    "La relación existe pero no es una recta. En la yunga, entre 500 y 2 000 metros, la "
    "prevalencia es incluso menor que en la costa. El ascenso arranca en la quechua y se "
    "acentúa en la puna, donde llega al 11,7 %. Un modelo que asumiera una línea recta se "
    "habría perdido esa forma: el ajuste con curvatura le gana por 15,6 puntos de AIC.",
    "Fuente: ENDES 2025 (INEI). Altitud del conglomerado según el marco muestral, de 1 a "
    "4 500 m. Los pisos siguen la clasificación de Pulgar Vidal.",
    "Tres paneles: un histograma de la altitud de la muestra, barras de prevalencia por "
    "piso altitudinal que crecen desde la costa hasta la puna, y una nube de puntos por "
    "tramos de 250 metros con una curva de tendencia ascendente.",
    como_leer=[
        "El primer panel dice cuánta gente vive a cada altura: la mayoría de la muestra "
        "está cerca del nivel del mar.",
        "El segundo agrupa por pisos. Las rayitas son el margen de error, y se ensanchan "
        "donde hay poca gente: la puna es la más ancha de todas.",
        "El tercero no agrupa: cada punto es un tramo de 250 metros. Sirve para ver si la "
        "subida es continua o si hay tramos donde baja.",
    ])}

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

<p>Se comparó la forma de la relación ajustando tres modelos —lineal, cuadrático y con
splines— y contrastándolos por AIC. El lineal queda <strong>15,6 puntos por detrás</strong>
del mejor. Es una diferencia grande: ajustar una recta a estos datos promedia el descenso
del tramo intermedio con el ascenso del alto, y puede acabar concluyendo que la altitud
«no importa». La forma es el hallazgo, no un tecnicismo.</p>

<div class="nota atencion">
  <strong>Una discrepancia que hay que contar, no esconder.</strong> En el tramo intermedio,
  el estudio sobre la ENDES 2019 reportó un aumento del 38 % (aPR 1,38; IC 1,04-1,84).
  Aquí sale lo contrario: una reducción del 19 % (aPR 0,81; IC 0,66-0,98). Los intervalos
  no se solapan, así que no es ruido de muestreo.
  <br><br>
  No tenemos explicación, y decirlo es parte del trabajo. Hay tres candidatas razonables:
  seis años de diferencia entre las olas, distinta composición de la muestra en ese tramo,
  o una especificación del modelo que no es exactamente la misma. Ninguna se puede
  comprobar con los datos disponibles. Queda como pregunta abierta bien planteada; en el
  tramo alto, donde sí coinciden ambos estudios, la evidencia es sólida.
</div>

{figura(
    "mapa_04_altitud_prevalencia.png",
    "Los dos mapas se parecen tanto que cuesta no sacar conclusiones",
    "Altitud a la izquierda, depresión a la derecha; la correlación entre ambos agregados "
    "departamentales es 0,63. Y precisamente por lo evidente que resulta conviene frenar: "
    "en el Perú, la altura viene acompañada de ruralidad, de pobreza, de lengua materna "
    "originaria y de menos servicios de salud. Cualquiera de esas cosas podría explicar el "
    "parecido.",
    "Fuente: ENDES 2025 (INEI). Correlación de Pearson entre agregados departamentales: "
    "r = 0,63 (p = 0,0008). Una correlación ecológica no dice nada sobre individuos.",
    "Dos mapas del Perú lado a lado, uno con la altitud media departamental y otro con la "
    "prevalencia de depresión. Los patrones oscuros coinciden en la sierra.")}

<div class="nota atencion">
  <strong>¿Sobrevive la altura al ajuste? Sí.</strong> Tras controlar por sexo, edad,
  educación, área de residencia, enfermedades crónicas, tabaco y alcohol, cada 100 metros
  de altura siguen asociándose con un odds ratio de {num(ajustado["or"], 3)}
  ({num(ajustado.ic_inf, 3)} – {num(ajustado.ic_sup, 3)}), lo que equivale a alrededor de un 9 %
  más de probabilidad por cada mil metros. La razón de prevalencia ajustada por encima de
  los 2 500 metros es 1,37, prácticamente idéntica al 1,41 que reportó el estudio peruano
  sobre la ENDES 2019. Que dos olas distintas de la encuesta den lo mismo refuerza el
  hallazgo.
  <br><br>
  <strong>Y aun así, esto no prueba que la altura cause depresión.</strong> Ninguna de las
  variables que pudimos ajustar mide pobreza, lengua materna ni distancia a un servicio de
  salud. Lo presentamos como una hipótesis que merece estudiarse, no como una conclusión.
</div>

{figura(
    "mapa_05_brecha_atencion.png",
    "En Cusco, 96 de cada 100 personas con tamizaje positivo no recibieron atención",
    "Este es el mapa que debería ordenar las prioridades. Todo el país está por encima del "
    "80 %, pero los departamentos donde la brecha es peor son, en buena medida, los mismos "
    "donde la prevalencia es más alta. La sierra sur acumula las dos cosas: más casos y "
    "menos atención.",
    "Fuente: ENDES 2025 (INEI). Calculado solo entre quienes dan positivo al tamizaje. Los "
    "departamentos con menos de 30 casos positivos no se estiman.",
    "Mapa del Perú por departamento con la brecha de atención en salud mental. Casi todo el "
    "territorio aparece en tonos oscuros, por encima del 80 %.")}
</section>"""
    return plantilla("07-geografia.html", "Geografía",
                     contenido + bloque_departamentos(), "8")


# ─────────────────────────────────────────────────────────────────────
# 9 · Factores
# ─────────────────────────────────────────────────────────────────────


def pagina_factores() -> str:
    """OR, RP y la paradoja del tabaco contada como historia."""
    bloques = tabla("tabla_21_modelos_por_bloques")
    inter = tabla("tabla_46_interacciones_filtradas")
    tabaco = bloques[bloques.variable == "fuma_12m"].iloc[0]
    sobreviven = int(inter.sobrevive.sum())
    significativas = int((inter.p_homogeneidad < 0.05).sum())

    contenido = f"""<section>
{cabecera("9", "activity", "Qué se asocia con la depresión")}
<p class="entradilla">Los datos dicen que fumar protege contra la depresión. La cifra es real y la conclusión no, y
la explicación de por qué es el mejor ejemplo de este boletín.</p>

<h3>La paradoja del tabaco</h3>
<p>Si se comparan sin más las personas que fumaron en el último año con las que no, salen
estas cifras: entre quienes fumaron, el 5,1 % tiene sintomatología depresiva; entre quienes
no, el 7,0 %. El odds ratio es {num(tabaco.or_crudo)}, claramente por debajo de 1. Leído
literalmente, fumar protegería.</p>

<p>Ahora miremos quién fuma. En el Perú, fumar es mucho más frecuente entre hombres. Y los
hombres tienen menos de la mitad de sintomatología depresiva que las mujeres. Así que al
comparar fumadores con no fumadores estamos comparando, en buena medida, hombres con
mujeres.</p>

<p>Cuando se separa el análisis por sexo y se comparan fumadores con no fumadores
<em>dentro</em> de cada grupo, el resultado se da la vuelta: el odds ratio ajustado es
<strong>{num(tabaco.or_ajustado)}</strong>. Fumar se asocia con más sintomatología, no con
menos.</p>

<div class="nota atencion">
  <strong>Esto se llama confusión.</strong> Una tercera variable —el sexo— está relacionada
  a la vez con la exposición y con el resultado, y distorsiona la comparación hasta
  invertirla. Le pasa lo mismo al consumo frecuente de alcohol: parece protector con un
  odds ratio de 0,72 y deja de serlo al ajustar. De las seis exposiciones que examinamos,
  dos cambian directamente de dirección.
</div>

{figura(
    "fig_07_confusion.png",
    "Ajustar no es un trámite: en algunos casos cambia el signo del resultado",
    "Antes de comparar dos grupos hay que descontar aquello que los diferencia por otras "
    "razones. Cada barra mide cuánto se mueve el resultado al hacerlo: si se mueve más de "
    "un 10 %, la variable descontada estaba distorsionando la comparación. Muchas lo "
    "superan. La hipertensión cambia un 41 % al tener en cuenta la edad, y el consumo "
    "problemático de alcohol un 40 % al tener en cuenta el sexo.",
    "Fuente: ENDES 2025 (INEI). Comparación entre el odds ratio crudo y el ajustado por "
    "Mantel-Haenszel.",
    "Gráfico de barras horizontales con el cambio porcentual entre el odds ratio crudo y el "
    "ajustado. Las barras que superan el umbral del 10 % aparecen destacadas.",
    como_leer=[
        "Cada barra es un par: un factor de riesgo y algo que podía estar distorsionando "
        "su medición, como la edad o el sexo.",
        "El largo dice cuánto cambia el resultado al descontar esa distorsión. Más largo, "
        "más engañaba la comparación cruda.",
        "El 10 % es el umbral convencional: por debajo se considera que la distorsión no "
        "era relevante.",
    ])}

<h3>El panorama completo</h3>
{figura(
    "fig_11_forest_or_ajustados.png",
    "El consumo problemático de alcohol multiplica por seis las probabilidades",
    "Es el factor más fuerte del modelo, por delante del sexo femenino. Vivir en la selva "
    "aparece del otro lado: se asocia con menos sintomatología que vivir en la costa. Los "
    "puntos grises son los que no permiten concluir nada, porque su rango de incertidumbre "
    "incluye el valor sin efecto.",
    "Fuente: ENDES 2025 (INEI). Odds ratios ajustados por sexo, edad, nivel educativo, área "
    "y región natural, estimados con el diseño muestral complejo. n = 28 553.",
    "Gráfico de puntos con líneas horizontales. El consumo problemático de alcohol tiene el "
    "valor más alto, alrededor de 6. El sexo femenino ronda 3. La selva aparece por debajo "
    "de 1.",
    ["La línea vertical punteada marca el <strong>1</strong>: ahí no hay ninguna asociación.",
     "Un punto <strong>a la derecha</strong> del 1 indica más probabilidad de "
     "sintomatología; a la izquierda, menos.",
     "La línea horizontal de cada punto es el margen de error. <strong>Si cruza el 1</strong>, "
     "los datos no permiten afirmar que exista asociación."])}

<h3>Dos formas de medir lo mismo</h3>
{figura(
    "fig_06_or_vs_rp.png",
    "El odds ratio exagera, pero aquí exagera poco",
    "Hay dos maneras de expresar cuánto más frecuente es algo en un grupo que en otro, y no "
    "coinciden: el odds ratio siempre se aleja más del 1 que la razón de prevalencias, y la "
    "diferencia crece cuando la condición es frecuente. Con un 7 % de prevalencia, la teoría "
    "dice que deberían parecerse. Y se parecen: la exageración media es del 5,3 %. "
    "Comprobarlo con los propios datos es más honesto que citarlo de un manual.",
    "Fuente: ENDES 2025 (INEI). La razón de prevalencias se estimó con regresión de Poisson "
    "y varianza robusta.",
    "Gráfico de puntos que compara el odds ratio con la razón de prevalencias de cada "
    "exposición. Los puntos se alinean cerca de la diagonal.",
    como_leer=[
        "Cada punto es un factor medido de dos formas distintas: una en el eje horizontal, "
        "la otra en el vertical.",
        "La diagonal marca dónde caerían si ambas coincidieran. Cuanto más se separa un "
        "punto de esa línea, más difieren las dos maneras de contar lo mismo.",
        "Aquí casi la tocan, que es lo esperable cuando la condición afecta a poca gente.",
    ])}

<h3>Cuándo un efecto no es igual para todos</h3>
<p>Con 30 000 observaciones, las pruebas estadísticas detectan diferencias mínimas. De las
{len(inter)} combinaciones que examinamos, {significativas} salían «significativas». Eso no
significa que {significativas} sean relevantes.</p>

<p>Por eso exigimos tres condiciones a la vez: que la diferencia siga siendo significativa
tras corregir por el número de pruebas, que los odds ratios de los dos grupos difieran al
menos vez y media, y que ambos grupos tengan casos suficientes.
<strong>Sobreviven {sobreviven}.</strong></p>

{html_tabla(inter[inter.sobrevive][["exposicion", "estratificador", "razon_or",
                                    "eventos_min_celda", "p_fdr"]].head(10),
            {"exposicion": "Exposición", "estratificador": "Difiere según",
             "razon_or": "Cuánto difieren", "eventos_min_celda": "Casos en la celda más pequeña",
             "p_fdr": "p corregido"},
            frozenset({"razon_or", "eventos_min_celda", "p_fdr"}),
            "Las interacciones que superan los tres criterios a la vez.")}

<div class="nota">
  <strong>Por qué un valor p pequeño no basta.</strong> Con una muestra grande, casi
  cualquier diferencia sale «estadísticamente significativa», incluso una que no cambiaría
  ninguna decisión. Lo que importa es el tamaño de la diferencia, y eso hay que mirarlo
  aparte.
</div>
</section>"""
    return plantilla("08-factores.html", "Factores asociados", contenido, "9")


# ─────────────────────────────────────────────────────────────────────
# 10 · El modelo
# ─────────────────────────────────────────────────────────────────────


def pagina_modelo() -> str:
    """La regresión logística explicada, con desempeño y mediación."""
    diag = tabla("tabla_24_diagnostico_logistica")
    med = tabla("tabla_43_efecto_total_vs_directo")

    contenido = f"""<section>
{cabecera("10", "trending-up", "El modelo")}
<p class="entradilla">Hasta aquí hemos mirado un factor a la vez. Un modelo los mira todos
juntos y responde otra pregunta: si dos personas se diferencian solo en una cosa, ¿cuánto
cambia eso?</p>

<h3>Qué es una regresión logística</h3>
<p>Imagine una balanza. Cada característica de una persona —su sexo, su edad, si tiene
hipertensión— pone un peso a un lado o al otro. La regresión logística es el procedimiento
que decide cuánto pesa cada cosa, mirando a la vez a las 28 553 personas del análisis.</p>

<p>Su resultado, el <strong>odds ratio</strong>, se lee así: un valor de 2 significa que la
característica duplica las probabilidades; uno de 0,5, que las reduce a la mitad; uno de 1,
que no cambia nada. Y lo hace <em>manteniendo lo demás constante</em>, que es justamente lo
que no podíamos hacer comparando de a dos.</p>

<h3>Efecto total y efecto directo</h3>
<p>Surge aquí una decisión que no es técnica sino conceptual. Si beber alcohol contribuye a
la obesidad, y la obesidad contribuye a la depresión, ¿debemos descontar la obesidad al
medir el efecto del alcohol?</p>

<p>Depende de qué se quiera saber. Si preguntamos «¿cuánto aporta beber, por todas las
vías?», la respuesta no debe descontarla: la ruta corporal es parte del efecto. Si
preguntamos «¿cuánto aporta beber por vías que no pasan por el cuerpo?», sí. Son dos
preguntas distintas, así que reportamos las dos.</p>

{figura(
    "fig_17_mediacion.png",
    "Descontar el peso corporal casi no cambia nada, y eso también es un resultado",
    "Los círculos son el efecto completo; los cuadrados, lo que queda tras descontar la ruta "
    "corporal. Están casi encima. La única excepción es la diabetes, donde alrededor de una "
    "cuarta parte del efecto sí viaja por ahí. Antes de calcular nada comprobamos el primer "
    "eslabón: de las cinco exposiciones, solo tres se asocian con la obesidad. Para las "
    "otras dos no hay ruta que descontar.",
    "Fuente: ENDES 2025 (INEI). Modelo A sin obesidad ni IMC; modelo B con ellos. La "
    "proporción mediada se calcula en la escala del logaritmo del odds ratio.",
    "Gráfico que compara dos estimaciones por exposición: el efecto total y el directo. Los "
    "pares de puntos casi coinciden salvo en la diabetes.",
    como_leer=[
        "Cada fila es un factor medido dos veces: el círculo cuenta todo su efecto; el "
        "cuadrado, solo la parte que no pasa por el peso corporal.",
        "La separación entre ambos símbolos es la parte del efecto que viaja por esa ruta. "
        "Si están pegados, el peso no hace de intermediario.",
        "La línea vertical del 1 separa lo que aumenta el riesgo de lo que lo reduce.",
    ])}

{html_tabla(med[["exposicion", "or_total_fmt", "or_directo_fmt", "lectura"]],
            {"exposicion": "Exposición", "or_total_fmt": "Efecto total",
             "or_directo_fmt": "Efecto directo", "lectura": "Lectura"},
            caption="Comparación entre el modelo A y el modelo B.")}

<h3>Qué tan bien funciona</h3>
{figura(
    "fig_12_roc_calibracion.png",
    "El modelo acierta dos de cada tres veces al comparar dos personas al azar",
    "Una curva ROC es como este juego: se toman dos personas al azar, una con sintomatología "
    "depresiva y otra sin ella, y se le pregunta al modelo cuál es cuál. Un AUC de 0,67 "
    "quiere decir que acierta dos de cada tres veces. Está por encima del azar, que sería "
    "0,5, y lejos de la certeza. Con esa precisión se puede decidir dónde hace falta un "
    "servicio de salud mental; para saber cómo está una persona concreta hace falta "
    "hablar con ella.",
    "Fuente: ENDES 2025 (INEI). Curva ROC y calibración por deciles de riesgo sobre 28 553 "
    "personas.",
    "Dos paneles. A la izquierda, la curva ROC, que se aleja de la diagonal del azar. A la "
    "derecha, la curva de calibración, con los puntos cerca de la diagonal ideal.",
    ["En la <strong>curva ROC</strong>, cuanto más se despega la línea de la diagonal, mejor "
     "distingue el modelo.",
     "En la <strong>curva de calibración</strong>, la diagonal es el ideal: cuando el modelo "
     "dice «10 %», debería acertar el 10 % de las veces.",
     "Que los puntos sigan la diagonal significa que las probabilidades son creíbles, aunque "
     "el modelo no distinga con mucha finura."])}

{html_tabla(diag, {"aspecto": "Qué se evaluó", "valor": "Resultado",
                   "veredicto": "Interpretación"},
            caption="Diagnóstico completo del modelo logístico.")}

<div class="nota">
  <strong>Un AUC de 0,67 no es un mal resultado, es el resultado correcto.</strong> Sería
  sospechoso que un puñado de variables sociodemográficas predijera con precisión algo tan
  complejo como la depresión. Si el modelo diera 0,95, lo primero que habría que buscar es
  el error.
</div>
</section>"""
    return plantilla("09-modelo.html", "El modelo", contenido, "10")


# ─────────────────────────────────────────────────────────────────────
# 11 · SHAP frente a OR
# ─────────────────────────────────────────────────────────────────────


def pagina_shap() -> str:
    """El contraste entre importancia predictiva y magnitud del efecto."""
    comp = tabla("tabla_30_shap_vs_or")
    ml = tabla("tabla_28_comparacion_modelos_ml")

    contenido = f"""<section>
{cabecera("11", "search", "Modelo y realidad: dos rankings que no coinciden")}
<p class="entradilla">El factor con el efecto más fuerte del estudio apenas ayuda a
predecir quién dará positivo. Suena a contradicción y no lo es: son dos preguntas
distintas, y cada una tiene su propia respuesta.</p>

<p>Además del modelo epidemiológico entrenamos algoritmos de aprendizaje automático
—bosques aleatorios, XGBoost, LightGBM— y les preguntamos qué variables usan para decidir.
La técnica se llama SHAP y reparte la responsabilidad de cada predicción entre las
características de la persona.</p>

<p>Esperábamos que su ranking se pareciera al de los odds ratios. Coinciden en un 35 %.</p>

{figura(
    "fig_14_shap.png",
    "El consumo problemático de alcohol es el primero por efecto y el decimoquinto por utilidad predictiva",
    "El sexo domina el panel de la izquierda con el 37 % de la importancia; el alcohol "
    "problemático apenas aparece. Y sin embargo su odds ratio es 6,07, el más alto del "
    "estudio. La explicación está en el denominador: afecta a 304 personas de 28 553. Un "
    "efecto enorme sobre muy poca gente casi no mueve la predicción media. El sexo es lo "
    "contrario: un efecto moderado sobre media población.",
    "Fuente: ENDES 2025 (INEI). Valores SHAP del mejor modelo de árboles, calculados sobre "
    "2 500 casos y precalculados para este boletín.",
    "Dos paneles. A la izquierda, barras horizontales con la importancia SHAP de cada "
    "variable; el sexo femenino encabeza con diferencia. A la derecha, la dispersión de los "
    "valores SHAP para esa variable.",
    ["Cada barra mide <strong>cuánto usa el modelo esa variable</strong>, en promedio, para "
     "decidir.",
     "No mide si la variable es importante para la salud: mide si ayuda a <em>adivinar</em>.",
     "Una variable puede tener un efecto grande y una barra pequeña, si afecta a poca "
     "gente."])}

{html_tabla(comp.head(10)[["etiqueta", "rango_or", "rango_shap", "or"]],
            {"etiqueta": "Variable", "rango_or": "Puesto por efecto",
             "rango_shap": "Puesto por utilidad predictiva", "or": "Odds ratio"},
            frozenset({"rango_or", "rango_shap", "or"}),
            "Los dos rankings, lado a lado. Cuanto mayor la diferencia, más informativa.")}

<h3>Por qué esto importa</h3>
<p>Porque llevan a decisiones opuestas y las dos son legítimas.</p>

<ul>
  <li>Si la pregunta es <strong>«¿sobre qué conviene intervenir?»</strong>, manda el efecto.
  Una intervención sobre el consumo problemático de alcohol tendría un impacto grande en
  quienes lo padecen.</li>
  <li>Si la pregunta es <strong>«¿a quién priorizo con recursos limitados?»</strong>, manda
  la utilidad predictiva. Ahí el sexo, la edad y la región ordenan mejor a la población.</li>
</ul>

<p>Confundirlas lleva a error en las dos direcciones: descartar una exposición relevante
porque no predice bien, o priorizar una intervención sobre una variable que solo predice
bien porque es frecuente.</p>

{figura(
    "fig_13_comparacion_modelos_ml.png",
    "Cuatro algoritmos, prácticamente el mismo resultado",
    "Se probaron cuatro maneras muy distintas de aprender de los mismos datos: desde una "
    "regresión clásica hasta tres algoritmos de los que se usan hoy en competiciones. Las "
    "cuatro se quedan entre 0,65 y 0,68. Cuando cambiar de método no mueve la aguja, el "
    "límite no está en el método sino en lo que la encuesta preguntó. El panel de la "
    "derecha es el exigente cuando el fenómeno es poco frecuente: mide si el modelo acierta "
    "al señalar, no solo si acierta al callar.",
    "Fuente: ENDES 2025 (INEI). Validación cruzada de cinco particiones, estratificada y "
    "agrupada por conglomerado muestral para evitar fuga de información.",
    "Dos paneles con curvas de rendimiento de cuatro modelos. Las curvas ROC de la izquierda "
    "están juntas y por encima de la diagonal; las de precisión-exhaustividad de la derecha "
    "también se solapan.",
    como_leer=[
        "Cada curva es un algoritmo distinto. Cuanto más se despega hacia la esquina "
        "superior izquierda, mejor distingue.",
        "La diagonal es el equivalente a lanzar una moneda. Las cuatro están por encima, "
        "pero no muy lejos.",
        "El panel derecho es el exigente cuando la condición es poco frecuente: penaliza "
        "señalar a demasiada gente con tal de no perderse a nadie.",
    ])}

{html_tabla(ml[["modelo", "auc_roc", "auc_pr", "sensibilidad", "especificidad"]],
            {"modelo": "Modelo", "auc_roc": "AUC-ROC", "auc_pr": "AUC-PR",
             "sensibilidad": "Sensibilidad", "especificidad": "Especificidad"},
            frozenset({"auc_roc", "auc_pr", "sensibilidad", "especificidad"}),
            "Comparación de algoritmos. La última fila es la referencia obligada.")}

<div class="nota atencion">
  <strong>Por qué no aparece la exactitud.</strong> Un modelo que responda «nadie tiene
  depresión» a todo el mundo acierta el 94 % de las veces sin haber mirado a nadie. Cuando
  el fenómeno afecta al 6 %, ese número no dice gran cosa: es la métrica más citada y la
  que menos informa en problemas como este.
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
  <strong>Esto no es un modelo fallido: es el resultado correcto.</strong>
  La depresión de una persona depende de su historia, sus duelos, su red de apoyo, su
  situación económica inmediata y su biología. Una encuesta de hogares mide sexo, edad,
  educación, dónde vive y unas pocas conductas. Con esas variables se puede describir
  <em>dónde se concentra</em> el problema en el país —y eso se hace bien, con intervalos
  estrechos y coherente con la literatura—, pero no se puede saber quién lo tiene.
  <br><br>
  Un modelo que con estas variables alcanzara un AUC de 0,90 sería motivo de sospecha, no
  de celebración: casi siempre significa que se coló una variable que ya contiene el
  desenlace. En este proyecto ese riesgo era real y concreto —<code>QS702</code> y
  <code>QS704A-I</code> se preguntan solo a quien ya marcó síntomas— y por eso se
  excluyeron desde el principio.
  <br><br>
  Reportar el techo honestamente vale más que maquillarlo. Un modelo con AUC 0,67 bien
  explicado orienta política pública sin prometer nada falso; el mismo modelo presentado
  como «detector» invita a usarlo sobre personas concretas, donde se equivoca cinco de
  cada seis veces.
</div>
</section>"""
    return plantilla("10-shap.html", "Modelo y realidad", contenido, "11")


# ─────────────────────────────────────────────────────────────────────
# 12 · Conclusiones
# ─────────────────────────────────────────────────────────────────────


def pagina_conclusiones() -> str:
    """Qué concluimos y qué no."""
    contenido = f"""<section>
{cabecera("12", "shield-check", "Qué significa esto")}
<p class="entradilla">Cinco conclusiones que los datos sostienen, y una lista igual de larga
de cosas que no podemos afirmar.</p>

<h3>Lo que muestran los datos</h3>

<p><strong>1. Una de cada catorce personas de 15 años o más presenta sintomatología
depresiva moderada o grave.</strong> El 6,98 %, con un margen entre 6,49 y 7,51. Es una
estimación representativa del país, no de quienes acuden a consulta.</p>

<p><strong>2. La brecha de atención es el hallazgo más grande.</strong> El 87,6 % de quienes
dan positivo no vio a un profesional en un año, y la cifra no baja del 80 % en ningún grupo.
El cuello de botella no está en detectar: está en atender.</p>

<p><strong>3. El riesgo se concentra donde ya se concentran otras desventajas.</strong>
Mujeres, personas mayores y adolescentes, quienes menos estudiaron, quienes viven en la
sierra sur y a mayor altura. Es el mismo mapa de siempre.</p>

<p><strong>4. La altura se asocia de forma consistente, y no de forma lineal.</strong> Por
encima de los 2 500 metros la razón de prevalencia ajustada es 1,37, casi idéntica a la que
encontró un estudio previo con la ENDES de 2019. Que dos olas coincidan refuerza el
hallazgo, aunque no lo convierte en causa.</p>

<p><strong>5. Ajustar cambia las conclusiones, a veces de signo.</strong> Fumar parecía
protector y no lo es. Es el recordatorio de que una comparación cruda entre dos grupos rara
vez responde la pregunta que uno cree estar haciendo.</p>

<h3>Lo que no podemos decir</h3>

<div class="nota">
  <strong>No podemos hablar de causas.</strong> El estudio es transversal: mide la exposición
  y el resultado en el mismo momento. No sabemos qué vino antes. Puede que beber en exceso
  contribuya a la depresión, que la depresión lleve a beber, o que un tercer factor produzca
  las dos cosas.
</div>

<div class="nota">
  <strong>No estamos midiendo depresión diagnosticada.</strong> El PHQ-9 es un tamizaje que
  responde la propia persona. Habrá quien puntúe alto sin tener un trastorno depresivo, y
  quien lo tenga sin puntuar alto.
</div>

<div class="nota">
  <strong>El punto de corte no está validado localmente.</strong> Usamos 10 porque es el
  estándar internacional, pero no conocemos un estudio que lo haya calibrado en población
  peruana. Si el umbral óptimo aquí fuera distinto, la prevalencia también.
</div>

<div class="nota">
  <strong>Falta quien no respondió.</strong> Se excluyó al 9,4 % que no completó el
  cuestionario. Si no responder tuviera relación con el estado de ánimo —cosa nada
  descartable—, estaríamos subestimando.
</div>

<div class="nota">
  <strong>La región natural es una aproximación.</strong> ENDES no la trae; la derivamos de
  la altitud del conglomerado, no de la clasificación oficial por distrito.
</div>

<h3>Qué haríamos con esto</h3>
<p>Si estos resultados tuvieran que traducirse en decisiones, apuntarían a tres cosas:</p>

<ul>
  <li><strong>Priorizar territorialmente.</strong> La sierra sur acumula más prevalencia y
  más brecha. No hace falta un estudio más para saber por dónde empezar.</li>
  <li><strong>Tamizar donde la gente ya está.</strong> Si el 88 % no llega a un servicio de
  salud mental, esperar en el servicio no funciona. El primer nivel de atención y las
  consultas por insomnio o cansancio son puertas más realistas.</li>
  <li><strong>Estudiar la altura en serio.</strong> La señal es consistente entre dos olas de
  la encuesta, pero ningún diseño transversal puede separarla de la pobreza y del acceso a
  servicios. Haría falta un estudio pensado para eso.</li>
</ul>

<div class="dos-columnas">
  <div>
    <h3>Sobre la reproducibilidad</h3>
    <p>Todo lo que hay en este boletín se regenera con un comando desde los microdatos
    públicos del INEI. Las tablas, las figuras, los mapas y este mismo texto salen del mismo
    proceso. Cualquiera puede descargar el código, ejecutarlo y obtener exactamente las
    mismas cifras — o encontrar dónde nos equivocamos.</p>
  </div>
  <div>
    <img class="ilustracion" src="{IMG}/ilustraciones/comunidad.svg"
         alt="Ilustración de un grupo de personas de distintas edades">
    <p class="credito-img">Ilustración original del proyecto</p>
  </div>
</div>
</section>"""
    return plantilla("11-conclusiones.html", "Conclusiones", contenido, "12")


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
         "d": '<a href="http://iinei.inei.gob.pe/microdatos/">Microdatos del INEI</a> · '
              "ENDES 2025, módulos CSALUD01 y RECH0"},
        {"q": "Límites geográficos",
         "d": "INEI 2023, distribuidos por geogpsperu / SuyoPomalia"},
        {"q": "Licencia", "d": "MIT · el análisis puede reutilizarse citando la fuente"},
    ])

    contenido = f"""<section>
{cabecera("13", "phone-call", "Si necesitas ayuda")}
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
  <blockquote class="frase-animo">
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
<ol>
  <li>Kroenke K, Spitzer RL, Williams JBW. <em>The PHQ-9: validity of a brief depression
  severity measure.</em> Journal of General Internal Medicine. 2001;16(9):606-613.</li>
  <li>Instituto Nacional de Estadística e Informática. <em>Encuesta Demográfica y de Salud
  Familiar — ENDES 2025.</em> Ficha técnica y microdatos. Lima, 2025.</li>
  <li>Zegarra-Rodríguez CA, Plasencia-Dueñas NR, Failoc-Rojas VE. <em>Disparities in the
  prevalence of screened depression at different altitudes in Peru: a retrospective analysis
  of the ENDES 2019.</em> PLOS ONE. 2022;17(12):e0278947.</li>
  <li>Basualdo-Meléndez GW, Hernández-Vásquez A, Barón-Lozada FA, Vargas-Fernández R.
  <em>Prevalence of depression and depressive symptoms at high altitudes: a systematic review
  and meta-analysis.</em> Journal of Affective Disorders. 2022;317:388-396.</li>
  <li>Kious BM, Bakian A, Zhao J, Mickey B, Guille C, Renshaw P, Sen S. <em>Altitude and risk
  of depression and anxiety: findings from the Intern Health Study.</em> International Review
  of Psychiatry. 2019;31(7-8):637-645.</li>
  <li>Basauri-Delgado M, Mesía-Guevara J-A, Saintila J. <em>Influence of sociodemographic,
  socioeconomic, and health factors on depression in the Peruvian population.</em> Journal of
  Primary Care &amp; Community Health. 2025;16.</li>
  <li>Organización Mundial de la Salud. <em>Trastornos depresivos (depresión).</em> 2023.</li>
  <li>von Elm E, Altman DG, Egger M, Pocock SJ, Gøtzsche PC, Vandenbroucke JP. <em>The STROBE
  Statement.</em></li>
  <li>Fox J, Monette G. <em>Generalized collinearity diagnostics.</em> Journal of the American
  Statistical Association. 1992;87(417):178-183.</li>
  <li>Lumley T. <em>Complex Surveys: A Guide to Analysis Using R.</em> Wiley, 2010.</li>
</ol>

<p class="ficha" style="margin-top:32px">
  Boletín elaborado en agosto de 2026 para el curso de Epidemiología 2026-2 de la Escuela
  Profesional de Estadística, Facultad de Ciencias Matemáticas, Universidad Nacional Mayor de
  San Marcos.
</p>
</section>"""
    return plantilla("12-cierre.html", "Ayuda y cierre", contenido, "13")


# ─────────────────────────────────────────────────────────────────────
# Orquestador
# ─────────────────────────────────────────────────────────────────────


def main() -> None:
    """Genera las trece páginas del boletín."""
    SALIDA.mkdir(parents=True, exist_ok=True)
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
        "09-modelo.html": pagina_modelo(),
        "10-shap.html": pagina_shap(),
        "11-conclusiones.html": pagina_conclusiones(),
        "12-cierre.html": pagina_cierre(),
    }
    for viejo in ("descriptivo.html", "factores.html", "modelo.html", "metodologia.html"):
        (SALIDA / viejo).unlink(missing_ok=True)

    for nombre, html in paginas.items():
        (SALIDA / nombre).write_text(html, encoding="utf-8")
        print(f"  {nombre:24s} {len(html) / 1024:6.1f} KB")

    print(f"\n{len(paginas)} páginas generadas en {SALIDA}")
    print("Para verlo:  python -m http.server 8000 --directory boletin")


if __name__ == "__main__":
    main()
