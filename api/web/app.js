/* Aplicación web del estimador de riesgo epidemiológico.
   ==========================================================================
   Todo el cálculo lo hace la API. El navegador solo recoge el perfil, pinta el
   resultado y dibuja el mapa. No se guarda nada: ni cookies, ni localStorage
   con datos del perfil, ni peticiones a terceros. Lo único que se recuerda es
   la preferencia de tema.
   ========================================================================= */

const estado = { contexto: null, geo: null, ultima: null };

/* ── Tema ─────────────────────────────────────────────────────────── */
/* El menú de la cabecera solo existe en pantallas estrechas: en escritorio los
   enlaces caben de sobra y el botón está oculto por CSS. */
function alternarMenu() {
  var c = document.getElementById('cabecera');
  var abierto = c.getAttribute('data-menu') === 'abierto';
  c.setAttribute('data-menu', abierto ? 'cerrado' : 'abierto');
  document.querySelector('.boton-menu').setAttribute('aria-expanded', String(!abierto));
}

function alternarTema() {
  const r = document.documentElement;
  const nuevo = r.getAttribute('data-tema') === 'oscuro' ? 'claro' : 'oscuro';
  r.setAttribute('data-tema', nuevo);
  localStorage.setItem('tema', nuevo);
  if (estado.ultima) dibujarMapa(document.getElementById('departamento').value);
}
(function () {
  const g = localStorage.getItem('tema');
  if (g) document.documentElement.setAttribute('data-tema', g);
  else if (window.matchMedia('(prefers-color-scheme: dark)').matches)
    document.documentElement.setAttribute('data-tema', 'oscuro');
})();

/* ── Utilidades ───────────────────────────────────────────────────── */
const num = (v, d = 1) => Number(v).toFixed(d).replace('.', ',');

function marcarPaso(n) {
  document.querySelectorAll('.paso').forEach((p) => {
    const i = Number(p.dataset.paso);
    p.classList.toggle('activo', i === n);
    p.classList.toggle('hecho', i < n);
  });
}

/* El arranque en frío de Render puede tardar cerca de un minuto. Se avisa en
   lugar de dejar la página aparentemente rota. */
async function pedir(url, opciones = {}) {
  const aviso = document.getElementById('despertando');
  const temporizador = setTimeout(() => { aviso.hidden = false; }, 2500);
  try {
    const r = await fetch(url, opciones);
    return r;
  } finally {
    clearTimeout(temporizador);
    aviso.hidden = true;
  }
}

/* ── Arranque ─────────────────────────────────────────────────────── */
async function iniciar() {
  try {
    const [ctx, geo] = await Promise.all([
      pedir('/mapa-datos').then((r) => r.json()),
      pedir('/geojson').then((r) => (r.ok ? r.json() : null)),
    ]);
    estado.contexto = ctx;
    estado.geo = geo;

    const sel = document.getElementById('departamento');
    sel.innerHTML = '<option value="">Selecciona tu departamento</option>' +
      ctx.departamentos.map((d) => `<option value="${d.codigo}">${d.nombre}</option>`).join('');
    sel.addEventListener('change', () => {
      dibujarMapa(sel.value);
      if (estado.ultima) mostrarComparacion(estado.ultima);
    });
    dibujarMapa('');
  } catch (e) {
    document.getElementById('aviso-form').textContent =
      'No se pudo contactar con el servidor. Revisa tu conexión e inténtalo de nuevo.';
  }
  cargarRecursos();
}

/* ── Recursos de ayuda ────────────────────────────────────────────── */
/* Vienen del catálogo verificado del servidor. El navegador no los inventa ni
   los completa: si el servidor no responde, se muestra el mínimo imprescindible. */
const RECURSOS_BASE = [
  { telefono: '113', nombre: 'Línea 113, opción 5 — Salud mental',
    descripcion: 'Orientación y apoyo psicológico gratuito del Ministerio de Salud.',
    meta: 'Gratuito · 24 horas, todos los días' },
  { telefono: '100', nombre: 'Línea 100 — Violencia familiar y sexual',
    descripcion: 'Atención del MIMP en castellano, quechua y aimara.',
    meta: 'Gratuito · 24 horas, todos los días' },
  { telefono: '106', nombre: 'SAMU — Emergencias médicas',
    descripcion: 'Atención prehospitalaria de urgencias y emergencias.',
    meta: 'Gratuito · 24 horas' },
];

function cargarRecursos() {
  document.getElementById('recursos').innerHTML = RECURSOS_BASE.map((r) => `
    <div class="recurso">
      <div class="numero">${r.telefono}</div>
      <h4>${r.nombre}</h4>
      <p>${r.descripcion}</p>
      <p class="meta">${r.meta}</p>
    </div>`).join('');
}

/* ── Mapa ─────────────────────────────────────────────────────────── */
function dibujarMapa(codigoSeleccionado) {
  const svg = document.getElementById('mapa');
  if (!estado.geo) {
    svg.innerHTML = '';
    document.getElementById('leyenda-mapa').textContent =
      'El mapa no está disponible en este momento.';
    return;
  }
  const oscuro = document.documentElement.getAttribute('data-tema') === 'oscuro';
  const escala = ['#dfeaf2', '#b9cbe0', '#7e9cc0', '#41689b', '#17456b', '#0d2b45'];
  const prevs = estado.contexto.departamentos.map((d) => d.prevalencia);
  const min = Math.min(...prevs), max = Math.max(...prevs);

  // Proyección lineal simple: basta para una silueta de referencia.
  let x0 = 180, x1 = -180, y0 = 90, y1 = -90;
  estado.geo.features.forEach((f) => recorrer(f.geometry, (x, y) => {
    x0 = Math.min(x0, x); x1 = Math.max(x1, x);
    y0 = Math.min(y0, y); y1 = Math.max(y1, y);
  }));
  const W = 300, H = 420, m = 8;
  const k = Math.min((W - 2 * m) / (x1 - x0), (H - 2 * m) / (y1 - y0));
  const px = (x) => m + (x - x0) * k;
  const py = (y) => H - m - (y - y0) * k;

  const partes = estado.geo.features.map((f) => {
    const cod = f.properties.codigo;
    const p = f.properties.prevalencia;
    const t = (p - min) / (max - min || 1);
    const relleno = p == null ? '#cbd5e0' : escala[Math.min(escala.length - 1,
      Math.floor(t * escala.length))];
    const sel = cod === codigoSeleccionado;
    return `<path d="${camino(f.geometry, px, py)}" fill="${relleno}"
      stroke="${sel ? '#d18d1f' : (oscuro ? '#24374a' : '#ffffff')}"
      stroke-width="${sel ? 2.4 : 0.5}" opacity="${codigoSeleccionado && !sel ? 0.45 : 1}">
      <title>${f.properties.nombre}: ${p == null ? 'sin dato' : num(p, 2) + ' %'}</title></path>`;
  });
  svg.innerHTML = partes.join('');

  const d = estado.contexto.departamentos.find((x) => x.codigo === codigoSeleccionado);
  document.getElementById('leyenda-mapa').textContent = d
    ? `${d.nombre}: ${num(d.prevalencia, 2)} % de prevalencia (IC 95 % ${num(d.ic_inf, 2)} – ${num(d.ic_sup, 2)}), sobre ${d.n} personas entrevistadas.`
    : 'Selecciona tu departamento para resaltarlo. El tono indica la prevalencia estimada.';
}

function recorrer(geom, fn) {
  const anillos = geom.type === 'Polygon' ? geom.coordinates : geom.coordinates.flat();
  anillos.forEach((anillo) => anillo.forEach(([x, y]) => fn(x, y)));
}

function camino(geom, px, py) {
  const anillos = geom.type === 'Polygon' ? geom.coordinates : geom.coordinates.flat();
  return anillos.map((anillo) =>
    'M' + anillo.map(([x, y]) => `${px(x).toFixed(1)},${py(y).toFixed(1)}`).join('L') + 'Z'
  ).join(' ');
}

/* ── Cálculo ──────────────────────────────────────────────────────── */
function leerPerfil() {
  const v = (id) => document.getElementById(id).value;
  const c = (id) => document.getElementById(id).checked;
  return {
    sexo: v('sexo'),
    grupo_etario: v('grupo_etario'),
    nivel_educativo: v('nivel_educativo'),
    region_natural: v('region_natural'),
    area: v('area'),
    edad: Number(v('edad')),
    consumo_frecuente_alcohol: c('consumo_frecuente_alcohol'),
    consumo_problematico_alcohol: c('consumo_problematico_alcohol'),
    fuma_12m: c('fuma_12m'),
    hipertension: c('hipertension'),
    diabetes: c('diabetes'),
    obesidad: c('obesidad'),
  };
}

async function calcular() {
  const aviso = document.getElementById('aviso-form');
  aviso.textContent = 'Calculando…';
  const perfil = leerPerfil();

  const r = await pedir('/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(perfil),
  });

  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    const detalle = Array.isArray(err.detail) && err.detail.length
      ? err.detail[0].msg : 'Revisa que la edad corresponda al grupo etario elegido.';
    aviso.textContent = `No se pudo calcular. ${detalle}`;
    return;
  }
  aviso.textContent = '';
  const pred = await r.json();
  estado.ultima = pred;

  // La tasa observada es el titular. Si no hay celda con suficientes casos, la
  // interfaz lo dice en vez de inventar una cifra.
  const rt = await pedir('/tasa-observada', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(perfil),
  });
  const tasa = rt.ok ? await rt.json() : null;

  // El resultado se revela ahora: el bloque de espera desaparece y el panel
  // entra con una transición corta. Aparecer de golpe se lee como un salto.
  document.getElementById('espera').hidden = true;
  const panel = document.getElementById('resultado');
  panel.hidden = false;
  panel.classList.add('entrando');
  panel.scrollIntoView({ behavior: 'smooth', block: 'start' });

  mostrarObservado(tasa);
  mostrarResultado(pred);
  mostrarComparacion(pred, tasa);
  mostrarFactores(pred);
  marcarPaso(7);
  await mostrarInterpretacion(perfil);
  marcarPaso(8);
  marcarPaso(9);
}

/* Pinta la frase de ánimo del banco cerrado. El texto llega ya elegido por el
   agente: aquí no se decide nada, solo se muestra. Si no viene ninguna —el caso
   de crisis— el recuadro se queda oculto. */
function mostrarAnimo(frase) {
  const caja = document.getElementById('tarjeta-animo');
  if (!frase || !frase.texto) { caja.hidden = true; return; }
  document.getElementById('animo-texto').textContent = frase.texto;
  document.getElementById('animo-fuente').textContent = frase.fuente;
  caja.hidden = false;
}

/* Dibuja cien puntos: la traducción visual de «X de cada 100». Una frecuencia
   natural se entiende mejor vista que leída, y aleja la lectura de «esta es mi
   probabilidad» hacia «esto le pasa a esta parte del grupo». */
function dibujarCien(pct) {
  const rejilla = document.getElementById('rejilla-cien');
  const enteros = Math.floor(pct);
  const resto = pct - enteros;
  rejilla.innerHTML = Array.from({ length: 100 }, (_, i) => {
    if (i < enteros) return '<i class="marcado"></i>';
    if (i === enteros && resto >= 0.25) return '<i class="parcial"></i>';
    return '<i></i>';
  }).join('');
  rejilla.hidden = false;
}

function mostrarObservado(t) {
  const cifra = document.getElementById('observado');
  const frase = document.getElementById('observado-frase');
  const detalle = document.getElementById('observado-detalle');
  const avisoImp = document.getElementById('aviso-impreciso');

  if (!t) {
    cifra.innerHTML = '\u2014';
    frase.textContent = 'No hay suficientes personas con este perfil en la encuesta para '
      + 'dar una cifra que se sostenga. Abajo queda la estimación del modelo.';
    document.getElementById('rejilla-cien').hidden = true;
    detalle.textContent = '';
    avisoImp.hidden = true;
    return;
  }

  cifra.className = 'observado-cifra';
  cifra.innerHTML = num(t.prevalencia, 1) + '<small> de cada 100</small>';
  frase.innerHTML = 'Entre las personas del mismo <strong>' + t.definido_por
    + '</strong> entrevistadas en la ENDES 2025, esa proporción dio positivo al '
    + 'tamizaje PHQ-9.';
  dibujarCien(t.prevalencia);
  detalle.textContent = 'Calculado sobre ' + t.n.toLocaleString('es-PE') + ' personas, de las '
    + 'cuales ' + t.eventos + ' dieron positivo. Intervalo de confianza del 95 %: '
    + num(t.ic_inf, 1) + ' % a ' + num(t.ic_sup, 1) + ' %.';

  if (t.impreciso) {
    avisoImp.hidden = false;
    avisoImp.innerHTML = '<strong>Estimación imprecisa.</strong> La muestra de este grupo es '
      + 'pequeña: la cifra real puede estar en cualquier punto entre ' + num(t.ic_inf, 1)
      + ' % y ' + num(t.ic_sup, 1) + ' %. Léela por su intervalo, no por el número puntual.';
  } else {
    avisoImp.hidden = true;
  }
}

function mostrarResultado(p) {
  const pct = p.probabilidad_pct;
  const clase = p.categoria_riesgo === 'alto' ? 'riesgo-alto'
    : p.categoria_riesgo === 'medio' ? 'riesgo-medio' : 'riesgo-bajo';
  // Las etiquetas nombran al grupo, no a quien consulta: «grupo de prevalencia
  // alta» describe una población; «riesgo alto» a secas se lee como veredicto.
  const texto = {
    alto: 'grupo de prevalencia alta',
    medio: 'grupo de prevalencia media',
    bajo: 'grupo de prevalencia baja',
  };

  document.getElementById('bloque-modelo').hidden = false;

  const el = document.getElementById('probabilidad');
  el.textContent = num(pct, 1) + ' %';
  el.className = 'estimacion-valor ' + clase;

  const cat = document.getElementById('categoria');
  cat.textContent = texto[p.categoria_riesgo];
  cat.className = 'categoria ' + clase;

  const barra = document.getElementById('barra');
  barra.style.width = Math.min(100, pct * 3) + '%';
  barra.className = clase;

  document.getElementById('incertidumbre').innerHTML =
    'Es lo que el modelo calcula para un perfil con estas características. '
    + '<strong>No es tu probabilidad</strong>: con un AUC de 0,67 ordena poblaciones '
    + 'por riesgo, pero no distingue a una persona de otra. '
    + '<a href="#limites">Ver por qué</a>.';
}

function mostrarComparacion(p, tasa) {
  const nacional = estado.contexto.nacional.prevalencia;
  const cod = document.getElementById('departamento').value;
  const dep = estado.contexto.departamentos.find((d) => d.codigo === cod);

  // Se compara la tasa observada, no la predicción. Poner una estimación del
  // modelo junto a prevalencias observadas mezcla dos cantidades distintas y
  // hace parecer que son la misma clase de dato.
  const propia = tasa ? tasa.prevalencia : p.probabilidad_pct;
  const etiqueta = tasa ? 'Personas con este perfil (observado)'
    : 'Este perfil (estimación del modelo)';

  let filas = `
    <div class="fila-comp destacada"><span>${etiqueta}</span>
      <b>${num(propia, 1)} %</b></div>
    <div class="fila-comp"><span>Prevalencia nacional</span><b>${num(nacional, 2)} %</b></div>`;

  if (dep) {
    filas += `<div class="fila-comp"><span>Prevalencia en ${dep.nombre}</span>
      <b>${num(dep.prevalencia, 2)} %</b></div>`;
    if (dep.brecha != null) {
      filas += `<div class="fila-comp"><span>Sin atención profesional en ${dep.nombre}</span>
        <b>${num(dep.brecha, 1)} %</b></div>`;
    }
    const razonDep = propia / dep.prevalencia;
    const razonNac = propia / nacional;
    filas += `<p class="pista">Este grupo está ${num(razonDep, 1)} veces por
      ${razonDep >= 1 ? 'encima' : 'debajo'} de la prevalencia de ${dep.nombre}, y
      ${num(razonNac, 1)} veces respecto de la nacional.</p>`;
  } else {
    filas += '<p class="pista">Selecciona tu departamento para comparar también con tu región.</p>';
  }
  document.getElementById('comparacion').innerHTML = filas;
}

function mostrarFactores(p) {
  const f = p.factores_contribuyentes;
  document.getElementById('factores').innerHTML = f.length
    ? f.map((x) => `<div class="factor"><span>${x.factor}</span>
        <span class="peso">×${num(x.odds_ratio, 2)}</span></div>`).join('') +
      '<p class="pista">Cada valor es cuánto multiplica ese factor las probabilidades, ' +
      'manteniendo el resto constante.</p>'
    : '<p class="pista">Ningún factor de este perfil eleva la estimación de forma apreciable ' +
      'respecto de la población general.</p>';
}

async function mostrarInterpretacion(perfil) {
  const caja = document.getElementById('interpretacion');
  caja.innerHTML = '<p class="pista">Redactando la interpretación…</p>';
  try {
    const r = await pedir('/interpretar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(perfil),
    });
    const d = await r.json();
    const etiqueta = d.modo === 'crisis'
      ? '<span class="etiqueta-modo crisis">Respuesta de seguridad</span>'
      : d.modo === 'llm'
        ? '<span class="etiqueta-modo">Redactada por un modelo y verificada</span>'
        : '<span class="etiqueta-modo">Redactada con plantillas sobre las cifras del modelo</span>';
    // La frase de ánimo viene también dentro del cuerpo, para los consumidores
    // que solo leen texto. Aquí se recorta y se muestra en su propio recuadro:
    // repetirla dos veces en la misma pantalla la vacía de efecto.
    const cuerpo = (d.texto || '').split('\n\n---\n\n«')[0];
    caja.innerHTML = etiqueta +
      `<div class="interpretacion-texto">${cuerpo.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')}</div>`;
    mostrarAnimo(d.frase_animo);
  } catch (e) {
    caja.innerHTML = '<p class="pista">No se pudo generar la interpretación en este momento. ' +
      'La estimación de arriba sigue siendo válida.</p>';
  }
}

/* ── Enlaces ──────────────────────────────────────────────────────── */
document.getElementById('calcular').addEventListener('click', calcular);
['sexo', 'grupo_etario', 'edad', 'nivel_educativo'].forEach((id) =>
  document.getElementById(id).addEventListener('change', () => marcarPaso(1)));
document.getElementById('departamento').addEventListener('change', () => marcarPaso(2));

iniciar();
