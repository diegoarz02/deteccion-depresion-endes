# Desplegar la aplicación en Render

Guía para seguir con el panel de Render abierto. Diez minutos.

El repositorio ya está publicado y todo lo que Render necesita está en su sitio. Aquí solo
se conecta y se pega una clave.

---

## Antes de empezar

Ten a mano:

- Una cuenta en [render.com](https://render.com) con GitHub conectado.
- La clave de Anthropic, si quieres que el agente redacte con modelo de lenguaje.
  **Es opcional**: sin ella la app funciona igual, con plantillas escritas sobre las cifras
  reales.

---

## 1 · Crear el servicio

1. En el panel, **New +** → **Web Service**.
2. **Connect a repository** → busca `deteccion-depresion-endes` → **Connect**.
   Si no aparece, pulsa **Configure account** y da acceso al repositorio.
3. Render lee el `render.yaml` de la raíz y rellena casi todo solo.

Comprueba que quedó así, y corrige lo que no coincida:

| Campo | Valor |
|---|---|
| **Name** | `depresion-endes` |
| **Region** | Oregon (US West) |
| **Branch** | `main` |
| **Root Directory** | *(vacío)* |
| **Runtime** | Python 3 |
| **Build Command** | `pip install --upgrade pip && pip install -r api/requirements.txt` |
| **Start Command** | `uvicorn api.main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | Free |

> **El nombre importa.** `depresion-endes` da la URL `depresion-endes.onrender.com`, que es
> exactamente la que el boletín ya tiene impresa. Con otro nombre, ese enlace queda roto.

---

## 2 · Pegar la clave del modelo

**Antes** de darle a crear, baja a **Environment Variables** y pulsa
**Add Environment Variable**:

| Key | Value |
|---|---|
| `ANTHROPIC_API_KEY` | *(tu clave)* |

Las otras cuatro —`PYTHON_VERSION`, `LOG_LEVEL`, `RATE_LIMIT`, `CORS_ORIGINS`— vienen del
`render.yaml` y no hay que tocarlas.

> **La clave se pega aquí y en ningún otro sitio.** Nunca en el repositorio, ni en un
> archivo, ni en un commit. Una clave que llega a GitHub hay que darla por comprometida
> aunque se borre después: queda en el historial.

Si no la pones, el servicio arranca igual. El agente responderá con plantillas construidas
sobre las cifras reales del modelo, que dicen lo mismo con menos variedad de estilo.

---

## 3 · Crear y esperar

Pulsa **Create Web Service**.

El primer despliegue tarda **2–4 minutos**. En el registro verás `pip install` y después:

```
Uvicorn running on http://0.0.0.0:10000
==> Your service is live 🎉
```

---

## 4 · Comprobar que quedó bien

Abre **https://depresion-endes.onrender.com/health**. Debe responder:

```json
{"estado":"ok","modelo_cargado":true,"version":"1.0.0"}
```

`modelo_cargado: true` es la parte importante. Si dijera `false`, el servicio está vivo pero
sin modelo — que es una avería distinta de estar caído, y por eso se distinguen.

Después abre **https://depresion-endes.onrender.com** y prueba el flujo entero:

- [ ] Rellena un perfil y pulsa calcular.
- [ ] Sale una cifra observada, la comparación, el mapa con tu departamento resaltado.
- [ ] Al final del resultado aparece el recuadro con la frase.
- [ ] La sección «Hasta dónde llega esto» está al fondo.

---

## 5 · El plan gratuito duerme

Es la particularidad que más sorprende: **tras 15 minutos sin visitas el servicio se apaga**,
y la siguiente persona que entre espera unos **50 segundos** a que despierte.

La app lo avisa sola con una banda ámbar arriba mientras tanto, así que nadie se queda
mirando una pantalla en blanco. Pero si vas a enseñarlo en clase, **ábrelo cinco minutos
antes** para que esté despierto.

Es el comportamiento normal del plan gratuito, no un fallo.

---

## Si algo falla

| Lo que ves | Qué pasa | Qué hacer |
|---|---|---|
| El build falla en `pip install` | Ruta mal | El Build Command debe decir `api/requirements.txt`, con la carpeta |
| «No open ports detected» | El puerto está fijo | El Start Command tiene que llevar `--port $PORT`, no un número |
| Health check en rojo | Ruta equivocada | En Settings → Health Check Path debe poner `/health` |
| La app carga pero da error al calcular | Faltan los datos | Comprueba que `api/datos/` tiene los cuatro `.json` en el repositorio |
| El agente no responde | Clave ausente o mal | Mira los logs. Sin clave debería caer a plantillas, no fallar |
| El boletín no puede consultar la API | CORS | `CORS_ORIGINS` debe incluir `https://diegoarz02.github.io` (sin ruta) |
| Tarda mucho la primera vez | Está despertando | Normal. Ver el punto 5 |

Los registros están en la pestaña **Logs** del servicio, en vivo.

---

## Después de un cambio en el código

El servicio tiene **Auto-Deploy: On Commit**, así que cada push a `main` publica solo.

Si un push no llega a desplegarse —pasa cuando el webhook de GitHub se desincroniza—, hay
dos formas de forzarlo:

- **Manual Deploy** → **Deploy latest commit**, en la esquina superior derecha.
- El **Deploy Hook** de Settings → Deploy: una URL secreta que dispara un despliegue con una
  petición POST. Útil para automatizar; trátala como una contraseña y usa *Regenerate hook*
  si alguna vez se expone.

Para comprobar qué versión está viva sin entrar al panel:

```bash
curl -s https://depresion-endes.onrender.com/health
```

Y en la pestaña **Events** se ve el historial: `Deploy live` con su hora, o `Deploy failed`
con el error.

Si lo que cambió fue el boletín y no la app, no hace falta tocar Render: eso vive en GitHub
Pages y se actualiza empujando la rama `gh-pages`.

---

## Datos medidos

Comprobado en local con el mismo comando que usa Render:

| | |
|---|---|
| Memoria con el modelo cargado | **55 MB** (límite del plan: 512 MB) |
| Dependencias de producción | 4 paquetes |
| `/health` sin clave del LLM | Responde 200 con `modelo_cargado: true` |
| Agente sin clave | Responde en modo degradado, no falla |
| Nodo de crisis | Se dispara antes del modelo y no muestra frase de ánimo |

El servicio cabe holgadamente porque no carga pandas, ni scikit-learn, ni geopandas: el
modelo se lee de un JSON de coeficientes y todo lo demás está precalculado.
