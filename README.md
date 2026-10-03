# Flowlytics

**Analítica de video para tiendas físicas.** Flowlytics mira las cámaras de un local y
responde lo que el dueño quiere saber: cuánta gente entra, dónde se para, por dónde
camina, cuánto espera en la fila y si la caja se queda sola. Todo en un panel web,
sin reconocimiento facial y sin guardar video continuo.

Este repositorio trae una demo completa: **clonas, ejecutas un archivo y ves seis
cámaras analizándose en vivo**. Tres son grabaciones de tiendas reales y tres son
transmisiones 24/7 de tiendas en Japón y Filipinas.

---

## Probarlo en 3 pasos

Necesitas **Python 3.10–3.13** e internet (para las cámaras de YouTube y para bajar el
modelo de detección la primera vez).

```bash
git clone https://github.com/P1p2gamer26/flowlytics.git
cd flowlytics
```

| Windows | Mac / Linux |
|---|---|
| Doble clic en **`iniciar.bat`** | `./iniciar.sh` |

La primera vez tarda unos minutos porque crea el entorno e instala las dependencias
(PyTorch, OpenCV, YOLO…). Después arranca en segundos. Al terminar abre solo
**http://localhost:8010/**. No pide usuario ni contraseña.

> Dale ~1 minuto a las cámaras para empezar a mandar datos. Las capas de calor y
> rutas se van llenando a medida que pasa gente.

Para pararlo: cierra la ventana (Windows) o pulsa `Ctrl-C` (Mac/Linux); se apagan
el panel y todas las cámaras.

---

## Qué vas a ver

### En vivo (página de inicio)

Todas las cámaras en una cuadrícula, reproduciéndose. Cada una tiene cinco capas:

| Capa | Qué muestra |
|---|---|
| **Normal** | El video tal cual |
| **Personas** | Lo que ve el detector: un recuadro por persona y el conteo, actualizado cada 2 s |
| **Calor** | Dónde se para la gente (últimas 24 h): rojo = mucho tiempo, verde = poco |
| **Rutas** | Los recorridos de cada persona en los últimos 30 min |
| **Zonas** | Las áreas que se miden: fila, caja, personal, entrada… |

Arriba a la derecha, **Capa para todas** cambia todas las cámaras a la vez.

### Las otras pestañas

- **Panel**: el resumen del día por negocio (visitantes, hora pico, espera en fila,
  cobertura del personal) y qué pasó hoy.
- **Cámaras**: el detalle de cada cámara; ahí se dibujan las zonas con clics sobre el
  video y se ve el mapa de calor por rango de fechas.
- **Avisos**: reglas para que te avise cuando la fila se alarga, la caja se queda sola
  o el local se llena (por correo o webhook), con horario de atención.
- **Conectar cámara / Cargar video**: añadir una cámara IP (RTSP), una URL de YouTube
  o subir un video.

---

## Cómo funciona

```
 fuente de video ──► worker (run_camera) ──► base de datos ──► API (Django REST) ──► panel (React)
 (archivo, RTSP,      YOLOv8 detecta personas    métricas cada 60 s,     /api/...           En vivo, Panel,
  YouTube en vivo)    ByteTrack las sigue        calor, rutas, eventos                       Cámaras, Avisos
                      zonas y líneas miden
```

1. **`correr_camaras`** lanza un worker (`run_camera <id>`) por cada cámara habilitada
   y lo relanza si se cae.
2. Cada worker toma ~2 cuadros por segundo, detecta personas con **YOLOv8n**
   (Ultralytics), las sigue con **ByteTrack** (supervision) y mide por zona: aforo,
   tiempo en fila, cruces de línea, recorridos y el mapa de calor. Guarda un resumen
   cada 60 s, no el video.
3. Si algo supera un umbral (fila larga, caja sola, local lleno) crea un **evento**,
   guarda un clip de 10 s y avisa según las reglas del negocio.
4. El panel lee todo por la API. En **En vivo**, el video que ves es el original
   (YouTube embebido o el archivo en bucle) y las capas se dibujan encima.

Las cámaras de YouTube se abren con `yt-dlp`; más detalle en
[`docs/camaras-en-vivo.md`](docs/camaras-en-vivo.md).

---

## Añadir tus propias cámaras

Desde el panel (**Conectar cámara** / **Cargar video**), o por consola:

```bash
# Windows: .venv\Scripts\python.exe   ·   Mac/Linux: .venv/bin/python
python manage.py shell -c "
from tenancy.models import Business
from cameras.models import Camera
negocio = Business.objects.get(name='Tiendas grabadas (demo)')
Camera.objects.create(business=negocio, name='Mi cámara',
                      source='https://www.youtube.com/watch?v=ID_DEL_VIDEO')   # o rtsp://..., o ruta a un .mp4
"
```

Luego, en **Cámaras → la cámara nueva**, dibuja al menos una zona (sin zonas no se
analiza). `correr_camaras` la detecta sola en menos de un minuto.

---

## Estructura

| Carpeta | Qué hay |
|---|---|
| `vision/` | El pipeline: detector, tracking, zonas, líneas, métricas, `run_camera`, `correr_camaras` |
| `cameras/` | Modelo de cámara/zonas, conexión a RTSP y YouTube, API de cámaras |
| `analytics/` | Métricas, eventos, mapa de calor, avisos y reportes CSV/PDF |
| `insights/` | Recomendaciones diarias con un LLM y comparativa anónima entre negocios |
| `tenancy/` | Negocios, usuarios y tipos de negocio (`rubros.py`: qué cifras ve cada rubro) |
| `dashboard/` | Sirve el panel; el build de React vive en `dashboard/static/dashboard/app/` |
| `frontend/` | Código del panel (React + Vite + Tailwind) |
| `demo/` | Videos de ejemplo y `camaras_demo.json` con las 6 cámaras y sus zonas |
| `docs/` | Documentación técnica, manual de usuario, cámaras en vivo, cartel de privacidad |
| `tests/` | ~660 tests (pytest) |

---

## Para desarrollar

```bash
# Tests del backend
.venv/bin/python -m pytest -q          # Windows: .venv\Scripts\python.exe -m pytest -q

# Panel (React): editar en frontend/src y recompilar al build que sirve Django
cd frontend
npm install
npm run build        # escribe en dashboard/static/dashboard/app/
npx vitest run       # tests del frontend
```

Variables útiles (en `.env` o en el entorno; ver `.env.example`):

| Variable | Por defecto | Para qué |
|---|---|---|
| `SIN_CUENTA` | `1` | Entra directo al panel como usuario demo. `0` exige login |
| `DETECTOR_IMGSZ` | `640` | Resolución de YOLO. `320` es 3× más rápido pero no ve gente pequeña |
| `SAMPLE_FPS` | `2` | Cuadros por segundo que analiza cada cámara |
| `ANTHROPIC_API_KEY` | — | Opcional: activa las recomendaciones diarias en lenguaje natural |
| `DATABASE_URL` | SQLite | `postgres://...` para producción |

Otros comandos: `python manage.py humo <video>` (prueba de punta a punta sobre un
video, deja un informe), `barrido_deteccion <video>` (elige `DETECTOR_IMGSZ` y
`SAMPLE_FPS` para tu máquina), `generate_insights`, `build_corpus`, `purge_clips`.

---

## Privacidad

- No se guarda video continuo: solo métricas agregadas por ventanas de 60 s y clips
  de 10 s cuando hay un evento (se borran a los 30 días).
- No hay reconocimiento facial ni se reconoce a la misma persona entre días.
- Al LLM solo se le envía texto agregado, nunca imágenes.
- La comparativa entre negocios es anónima y nunca se muestra con menos de 5
  negocios en el grupo.
- Para un local real hay un cartel listo para imprimir en
  [`docs/cartel-privacidad.md`](docs/cartel-privacidad.md).

---

## Problemas comunes

| Síntoma | Qué hacer |
|---|---|
| Una cámara dice **Sin señal** | Mira `logs/camara_<id>.log`. Si es de YouTube, puede que la transmisión cambió de ID: ver [`docs/camaras-en-vivo.md`](docs/camaras-en-vivo.md) |
| La capa **Personas** no muestra imagen | El worker aún no arranca (espera 1 min) o se cayó: `logs/supervisor.log` |
| Todo va lento | Baja `DETECTOR_IMGSZ` a `480` o `SAMPLE_FPS` a `1`, o deshabilita cámaras desde Cámaras |
| `pip install` falla | Usa Python 3.11 o 3.12, las versiones más probadas con PyTorch y OpenCV |
| Puerto 8010 ocupado | Cambia `8010` en `iniciar.bat` / `iniciar.sh` |
