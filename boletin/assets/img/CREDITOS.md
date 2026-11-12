# Créditos de las imágenes del boletín

Última actualización: 2026-11-12

Todos los archivos están **descargados o generados en local**: imágenes, iconos,
ilustraciones y también las tipografías. El boletín no hace ninguna petición a otro
dominio, así que funciona sin conexión y en cualquier hosting estático.

Las fuentes se autoalojan desde la corrida final. Antes se cargaban desde Google, lo
que contradecía esta misma afirmación y hacía que la página cambiara de aspecto a
mitad de carga con una conexión mala. Las descarga
`codigo/scripts/descargar_fuentes.py`, que trae solo los subconjuntos latinos y
deduplica por contenido: Fraunces e Inter son variables y Google sirve el mismo
archivo para cada peso, de modo que catorce descargas son en realidad cuatro
archivos (254 kB en total, frente a 892 kB sin deduplicar).

---

## Criterio editorial

En salud mental, la elección de imágenes no es un asunto decorativo.

- **No se usan fotografías de personas reales.** Una persona identificable junto a la
  palabra «depresión» queda asociada a ella para siempre; estigmatiza y expone.
- **Se evitan los clichés que estigmatizan:** la cabeza entre las manos en blanco y
  negro, la silueta en el rincón oscuro, la botella junto a la persona derrumbada.
  Refuerzan el estigma y envejecen mal.
- **Las ilustraciones muestran acompañamiento, conversación y búsqueda de ayuda**, no
  sufrimiento. El mensaje del boletín es que detectar a tiempo sirve.
- Las figuras humanas son siluetas sin rasgos: no representan a nadie en concreto.

---

## Ilustraciones

**Originales de este proyecto**, dibujadas en SVG con la paleta del boletín.

Se descartaron los bancos de ilustraciones libres (unDraw, Storyset) porque ninguno
ofrece descarga programática estable —el CDN público de unDraw responde 404— y
enlazar en caliente rompería el boletín sin conexión. Dibujarlas aquí garantiza además
que el color de acento coincide exactamente con el del resto del sitio.

| Archivo | Descripción | Autor | Licencia | Peso |
|---|---|---|---|---|
| `ilustraciones/conversacion.svg` | Dos personas conversando, una escuchando a la otra | Proyecto de Epidemiología 2026-2, UNMSM | MIT (la del repositorio) | 1.3 KB |
| `ilustraciones/apoyo.svg` | Una persona acompañando a otra, con una mano en el hombro | Proyecto de Epidemiología 2026-2, UNMSM | MIT (la del repositorio) | 1.1 KB |
| `ilustraciones/busqueda_ayuda.svg` | Cien figuras: doce cruzan una puerta abierta y ochenta y ocho se quedan fuera | Proyecto de Epidemiología 2026-2, UNMSM | MIT (la del repositorio) | 17.0 KB |
| `ilustraciones/comunidad.svg` | Un grupo de personas de distintas edades, juntas | Proyecto de Epidemiología 2026-2, UNMSM | MIT (la del repositorio) | 1.4 KB |
| `ilustraciones/deteccion.svg` | Una lupa sobre un gráfico ascendente, la idea de detectar a tiempo | Proyecto de Epidemiología 2026-2, UNMSM | MIT (la del repositorio) | 1.1 KB |
| `ilustraciones/territorio.svg` | Una silueta del territorio con marcadores de ubicación | Proyecto de Epidemiología 2026-2, UNMSM | MIT (la del repositorio) | 1.2 KB |

---

## Iconos

**Lucide** — <https://lucide.dev> · licencia **ISC** · no exige atribución, pero se
cita igualmente. Descargados desde `unpkg.com/lucide-static` el 2026-11-12 y teñidos con
el navy del proyecto.

| Archivo | Uso en el boletín | Estado |
|---|---|---|
| `iconos/brain.svg` | Sección 2 · qué es la depresión | ya estaba |
| `iconos/heart-handshake.svg` | Sección 4 · detección temprana y apoyo | ya estaba |
| `iconos/users.svg` | Sección 7 · perfil sociodemográfico | ya estaba |
| `iconos/map-pin.svg` | Sección 8 · geografía | ya estaba |
| `iconos/activity.svg` | Sección 9 · factores asociados | ya estaba |
| `iconos/trending-up.svg` | Sección 10 · el modelo | ya estaba |
| `iconos/search.svg` | Sección 11 · modelo frente a realidad | ya estaba |
| `iconos/phone-call.svg` | Sección 13 · líneas de ayuda | ya estaba |
| `iconos/shield-check.svg` | Encuadre ético | ya estaba |
| `iconos/clipboard-list.svg` | Sección 6 · cómo lo medimos | ya estaba |
| `iconos/database.svg` | Sección 5 · de dónde salen los datos | ya estaba |
| `iconos/message-circle-heart.svg` | Sección 3 · la problemática | ya estaba |
| `iconos/triangle-alert.svg` | Avisos y limitaciones | ya estaba |
| `iconos/map.svg` | Mapas | ya estaba |

---

## Otros recursos

| Archivo | Descripción | Fuente | Licencia |
|---|---|---|---|
| `logo_unmsm.jpg` | Escudo de la Universidad Nacional Mayor de San Marcos | Institucional | Uso académico institucional |
| `flujograma_strobe.png` | Diagrama de conformación de la muestra | Generado por este proyecto | MIT |
| `dag_causal.png` | Grafo acíclico dirigido del estudio | Generado por este proyecto | MIT |
| `mapa_*.png` | Cartografía | Generados por este proyecto sobre límites del INEI 2023 (geogpsperu / SuyoPomalia) | MIT; límites de uso público |
