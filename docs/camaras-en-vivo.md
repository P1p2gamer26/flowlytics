# Cámaras en vivo

Cualquier transmisión pública de YouTube sirve como cámara: se pega la URL del video
en vivo como fuente (`Camera.source`) y el worker la abre como si fuera una cámara IP.

## Cómo funciona

1. `Camera.url_conexion()` detecta que la fuente es de YouTube y, con `yt-dlp`, la
   convierte en la URL HLS del stream a 480p (`cameras/models.py: resolver_youtube`).
2. Esa URL caduca a las ~6 h, así que `run_camera` la vuelve a resolver en cada
   reconexión.
3. En el panel, la pantalla **En vivo** muestra el reproductor de YouTube embebido y
   dibuja encima las capas (personas, calor, rutas, zonas) con lo que guardó el worker.

## Las cámaras de ejemplo

| Cámara | URL | Qué se ve |
|---|---|---|
| Umineko Shouten (Japón) | https://www.youtube.com/watch?v=3o9aoRyrvAk | Panadería vista desde arriba: caja, mostrador y piso |
| Rachel Store (Filipinas) | https://www.youtube.com/watch?v=7p3ZFFr3ksE | Mostrador de una tienda de mercado con fila de clientes |
| Boy Sayong (Filipinas) | https://www.youtube.com/watch?v=sShWJMKFV-k | Puesto del mercado de Agdao visto desde la calle |

Las de Filipinas son del canal [Maria Deseo](https://www.youtube.com/@MariaDeseo-Philippines/streams),
que tiene una docena de cámaras más.

**Los IDs de YouTube cambian** cuando el dueño reinicia la transmisión. Si una cámara
queda en "Sin señal" mucho rato, busca el ID nuevo en el canal y actualiza la fuente:

```bash
python -m yt_dlp --flat-playlist --print "%(id)s %(live_status)s %(title)s" \
  "https://www.youtube.com/@MariaDeseo-Philippines/streams"
python manage.py shell -c "from cameras.models import Camera; Camera.objects.filter(pk=9).update(source='https://www.youtube.com/watch?v=NUEVO_ID')"
```

## Rendimiento

El costo está en la inferencia de YOLO, no en leer el stream.

- `DETECTOR_IMGSZ=640` (por defecto en `iniciar.*`): unos 40 ms por cuadro en un
  portátil normal; detecta bien a la gente en cámaras cenitales.
- `DETECTOR_IMGSZ=320`: 3 veces más rápido, pero **deja de ver** a las personas pequeñas
  o vistas desde arriba (en Umineko pasa de 1 persona a 0). Úsalo solo si la máquina
  no da abasto.
- `OMP_NUM_THREADS=2` viene por defecto: más hilos de torch por worker se estorban
  cuando hay varias cámaras a la vez.

## Dejarlas corriendo en un servidor Linux

`python manage.py correr_camaras` mantiene un worker por cámara habilitada y lo
relanza si se cae. Como servicio de usuario de systemd:

```ini
# ~/.config/systemd/user/flowlytics-camaras.service
[Unit]
Description=Flowlytics: analisis de camaras

[Service]
WorkingDirectory=%h/flowlytics
ExecStart=%h/flowlytics/.venv/bin/python manage.py correr_camaras
Restart=always
RestartSec=30
Nice=10

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload && systemctl --user enable --now flowlytics-camaras
loginctl enable-linger "$USER"    # que siga corriendo al cerrar la sesión
```
