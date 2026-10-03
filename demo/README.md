# Banco de videos de demo (sin cámaras reales)

El worker trata un archivo de video como si fuera una cámara. Así se puede
desarrollar, demostrar y medir precisión sin RTSP físico.

## Cómo usar

1. Deja tus videos reales en `demo/videos/<contexto>/`, por ejemplo:
   ```
   demo/videos/cctv/tienda_iprox.mp4
   demo/videos/tienda/caja.mp4
   ```
   (Esta carpeta está en `.gitignore`: los videos no se versionan, pesan mucho.)
2. Crea una cámara desde el panel de administración o el dashboard con:
   `source = file://demo/videos/tienda/entrada.mp4`
3. Abre la página de Cámaras y pulsa **Dibujar zona**: el editor carga el primer
   frame del video y dibujas las zonas sobre la imagen real.
4. Corre el worker:
   ```bash
   # rápido (tiempo simulado) y en bucle — para generar métricas al instante
   python manage.py run_camera <id>

   # como feed vivo (espera el tiempo del video) — para demostrar en el dashboard
   python manage.py run_camera <id> --tiempo-real

   # una sola pasada — para benchmarks
   python manage.py run_camera <id> --una-pasada
   ```

Para probar un video de punta a punta sin abrir el navegador:
`python manage.py humo demo/videos/cctv/tienda_iprox.mp4` (ver el README principal).

## El banco de prueba: tres cámaras de tienda

**Es el único corpus del proyecto.** Se trae con un comando y no se versiona
(pesa ~140 MB):

```bash
python demo/traer_videos.py
```

| Ruta | Qué es | Resolución | Duración |
|---|---|---|---|
| `cctv/tienda_usa.mp4` | Tienda en EEUU, cámara de esquina alta | 1920×1080 | 60 s |
| `cctv/tienda_iprox.mp4` | Tienda pequeña con caja y pasillos | 1270×720 | 111 s |
| `cctv/super_caja.mp4` | Caja de supermercado, vista alta | 1920×1080 | 299 s |

Las tres son **cámaras fijas colgadas en alto dentro de un local**, que es lo
que este producto va a ver de verdad.

### Por qué se tiró el corpus anterior

El 6-sep-2026 se miraron por primera vez las detecciones dibujadas sobre los
frames, y el material resultó no parecerse al caso de uso: una película en
blanco y negro de archivo en plano cerrado, un video de celular grabado
**caminando** por un centro comercial, un pasillo de metro con dos personas y un
CCTV lavado donde la gente eran motas de pocos píxeles. Nada de eso es una
cámara fija en una tienda.

Toda medición hecha contra aquello describía un escenario que no existe en
producción. El detalle está en `docs/notas/auditoria-corpus-6sep.md`; el caso más
claro: con gente grande en el cuadro, `imgsz` 416 y 640 detectan lo mismo, así
que el corpus viejo habría dictaminado "subir la resolución no sirve" — la
conclusión contraria a la correcta.

**No añadas videos al banco sin comprobar que son cámara fija, en alto y dentro
de un local.** Un clip bonito que no cumple eso empeora las mediciones en vez de
mejorarlas.

La resolución del video puede cambiar libremente: las zonas se escalan
proporcionalmente desde el frame de referencia que guardó el editor.

## Anotación y reporte de precisión

`demo/referencia.json` guarda, por video, el conteo anotado a mano y las líneas
sobre las que contar cruces. Es la **verdad**: el sistema no se mide contra su
propia salida.

- `entradas`, `salidas`: personas que cruzaron la línea en cada sentido (a mano).
- `aforo_max`: máximo de personas simultáneas (opcional; `null` = no anotado).
- `lineas`: `[{ "name": "puerta", "puntos": [[x0,y0],[x1,y1]], "invertir": false }]`
  en píxeles del frame de referencia (`ancho`/`alto`). El sentido se corrige con
  `invertir` si entrada y salida salen al revés.

### El camino completo, de un video a un número

1. **Deja el video** en `demo/videos/<contexto>/`.
2. **Prepara la entrada** (saca ancho, alto y fps del archivo — son los que
   escalan la línea, no los adivines):

   ```bash
   .venv/bin/python manage.py anotar_referencia demo/videos/tienda/entrada.mp4 \
       --ruta tienda/entrada.mp4 --contexto tienda
   ```

3. **Dibuja la línea** en `demo/referencia.json`, en la clave `lineas`: dos
   puntos en píxeles del frame, por donde de verdad pasa la gente. El editor de
   zonas del panel sirve para leer coordenadas sobre el frame real.
4. **Mira el video y cuenta a mano.** Esto no lo puede hacer el sistema: es
   justamente lo que se usa para juzgarlo.

   ```bash
   .venv/bin/python manage.py anotar_referencia demo/videos/tienda/entrada.mp4 \
       --ruta tienda/entrada.mp4 --entradas 37 --salidas 35 --aforo-max 6
   ```

5. **Mide y publica:**

   ```bash
   .venv/bin/python manage.py reporte_precision --publicar
   ```

   Escribe `demo/reporte_precision.md` y actualiza la sección de precisión de
   `docs/tecnico.md`. El reporte trae, además del promedio, la diferencia
   absoluta por métrica, una sección "Dónde falla" con lo que pasa del 15% de
   error, y la lista de los videos sin anotar. Un video sin conteo a mano se
   omite del promedio, pero aparece por su nombre: no desaparece.

Los porcentajes son una media simple por video, sin ponderar por duración ni por
cuánta gente pasó. Un clip de dos segundos pesa lo mismo que uno de dos minutos:
por eso el reporte muestra también la diferencia absoluta.

## El códec importa

Los videos deben quedar en H.264 (`avc1`). OpenCV también lee `mp4v`, así que un
archivo así funciona en el worker y **falla solo en el navegador**: el editor de
zonas se queda en negro sin decir por qué. Para comprobarlo:

```bash
python manage.py verificar_videos
```

Sale con error y lista las cámaras cuyo video no es reproducible. Para
arreglarlos, `python demo/transcodificar_videos.py` los reconvierte (si el
archivo está bloqueado, para antes el `run_camera` que lo esté leyendo).
