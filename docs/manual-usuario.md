# Manual de usuario

Guía para el dueño de un negocio. No necesitas saber de programación.

## 1. Crear tu cuenta y tu negocio

Entra a `/registro/`, elige usuario y contraseña, y el nombre y tipo de tu
negocio. Al terminar entras directo a los primeros pasos.

## 2. Primeros pasos (onboarding)

En `/onboarding/` verás una lista: negocio creado ✅, agregar una cámara, dibujar
una zona. Cada paso se marca solo cuando lo haces.

La lista de zonas que propone el onboarding depende del tipo de negocio que
elegiste al registrarte (por ejemplo "Mesas" si elegiste Cafetería, "Cajas" si
elegiste Tienda); puedes dibujar cualquier otra zona además.

## 3. Colgar una cámara de verdad

Si quieres que el sistema funcione con una cámara IP en vez de con un video
cargado, entra por **"Conectar cámara"** en el menú. Necesitas:

- La dirección del stream de la cámara. Suele estar en el manual o en la app
  del fabricante. Tiene forma de `rtsp://192.168.1.50:554/stream1` y cambia
  con la marca: Hikvision suele usar
  `rtsp://IP:554/Streaming/Channels/102`, Dahua
  `rtsp://IP:554/cam/realmonitor?channel=1&subtype=1`. El sub-stream (el
  segundo) va a menor resolución y es el que conviene para esto.
- El usuario y la contraseña de la cámara, en sus casillas **separadas**. No los
  pongas dentro de la dirección: van en sus propias casillas y así se guardan
  cifrados.
- Que la cámara esté en la misma red que el servidor.

Antes de guardar, dale a **"Probar conexión"**. El sistema te dice qué pasa:

| Mensaje | Qué hacer |
|---|---|
| La dirección tiene que empezar por `rtsp://` | Revisa la dirección: copia la que publica el fabricante. |
| No responde nadie en esa IP | La cámara está apagada, le cambió la IP, o no está en la misma red que el servidor. |
| El equipo responde, pero no entrega video | Revisa el usuario y la contraseña; también que la ruta del stream sea la correcta. |
| Conecta, pero no llega ninguna imagen | La cámara probablemente emite en H.265: cambia ese stream a H.264 en la configuración de la cámara. |

Si todo va bien, guarda la cámara. Verás su imagen en directo y puedes
dibujar zonas y la línea de entrada igual que con un video.

**Mientras el sistema está corriendo**, si la conexión se cae el worker sigue
reintentando solo. En la pantalla de la cámara aparece "sin señal" con el
motivo y el contador de reconexiones; no hay que reiniciar nada.

## 4. Configurar tu primera cámara

En `/camaras/` agregas una cámara (una URL RTSP, o un video para probar). Cada
cámara tiene su propia página en `/camaras/<id>/`, donde puedes dibujar una
zona sobre la imagen para decidir qué área medir (sala, fila de caja,
mostrador). El sistema puede sugerirte una zona automáticamente a partir de
por dónde camina la gente; tú decides el nombre y qué significa.

Para medir cuánta gente entra al local, eliges **"Línea de entrada (2 clics)"**
y marcas dos puntos sobre la imagen, uno a cada lado de la puerta. Una flecha
verde señala hacia qué lado cuenta como entrada; si apunta hacia afuera, el
botón **"Invertir sentido"** la voltea de inmediato sin tener que volver a
dibujarla.

## 5. Leer tu panel

El panel (`/`) muestra la cifra principal **"Entraron"** con su conteo de
entradas y salidas al cruzar la línea. Si todavía no hay ninguna línea dibujada,
el panel muestra **"Visitantes del día"** y avisa cómo configurarla. Ambas cifras
son distintas: "Visitantes del día" suma presencias por zona y cuenta dos veces
a quien pasa por dos zonas, mientras que la línea cuenta personas reales que
cruzaron la puerta.

El panel también incluye aforo pico, tiempo de cola y eventos (fila larga, caja
desatendida, aforo excedido).

Si usas una cámara en vivo, el panel de esa cámara puede mostrar "sin señal"
cuando la conexión se cae. El sistema sigue reintentando solo; no hay que
reiniciar nada.

## 6. Qué mide tu panel según tu negocio

Las cinco cifras principales que muestra tu panel no son las mismas para todos
los negocios: cada tipo de negocio tiene sus propias métricas y el orden de
importancia. La primera cifra que aparece en tu panel es la más importante para
tu tipo de negocio.

| Tipo de negocio | Métrica principal | Zonas sugeridas para medir |
|----------------|-------------------|----------------------------|
| Cafetería      | Permanencia en mesa | Mesas, Barra, Fila para pedir, Entrada |
| Restaurante    | Permanencia en mesa | Salón, Espera para mesa, Caja, Entrada |
| Tienda         | Cola en caja      | Cajas, Fila de caja, Pasillo principal, Entrada |
| Aula           | Asistencia máxima | Aula, Entrada |
| Otro           | Visitantes del día | Zona principal, Entrada |

Estas configuraciones vienen definidas en `tenancy/rubros.py`. Si allí se
modifican, este documento se actualizará en consecuencia.

## 7. Descargar reportes

Desde el panel, los enlaces **Descargar reporte: CSV / PDF**. El CSV se abre
en Excel; el PDF trae una tabla por día y un gráfico. Por defecto son los
últimos días disponibles; puedes pedir otro rango con
`?desde=YYYY-MM-DD&hasta=YYYY-MM-DD` en la URL.

## 7. Invitar a alguien de tu equipo

En `/invitar/` generas un enlace con un token. Compártelo por el medio que
prefieras (la app no manda correos). Quien lo abra crea su cuenta unida a TU
negocio y a ningún otro.

## 8. Tu plan

Tu plan define cuántas cámaras puedes tener (`max_camaras`) y cuántos días se
guardan los datos (`retencion_dias`). Si intentas pasarte del límite de
cámaras, el sistema te avisa. Cambiar de plan es una gestión con el
administrador de la plataforma.

## Preguntas frecuentes

- **¿Puedo ver los datos de otro negocio?** No. Cada negocio ve solo lo suyo:
  cualquier intento de leer datos de otro negocio recibe un error.
- **¿Necesito una cámara para probar?** No: pídele al administrador que corra
  `manage.py seed_demo` y tendrás un negocio "Demo" con datos de ejemplo,
  sin cámaras ni videos.
- **¿Se guarda video mío?** No de forma continua: solo métricas agregadas por
ventanas de 60 s, y clips de 10 s únicamente ante eventos configurados, con
retención de 30 días. No hay reconocimiento facial.

- **¿Cuál es la diferencia entre permanencia y espera?** — permanencia es cuánto
se queda un cliente en las zonas donde se supone que esté (mesa, salón,
pasillo); espera es cuánto está en la fila. Ni una ni otra cuentan al
personal.

- **¿Mi panel no muestra la espera en fila?** — porque tu rubro no la pone entre
  sus cifras, o porque no hay ninguna zona de tipo fila dibujada. Un guion
  es "no hay dónde medirlo", no "es cero".

## 9. Por dónde va la gente

Abre `/camaras/<id>/` con un video ya analizado. Mientras el video se
reproduce, cada persona detectada deja detrás una cola corta y desvanecida que
muestra hacia dónde se está moviendo en ese instante.

Debajo del video hay dos formas de revisar los recorridos completos:

- **"Mostrar todos los recorridos"** congela el primer frame del análisis y
  dibuja, sobre esa imagen fija, la línea completa de todas las personas
  vistas durante ese video.
- **Tocar una persona** en el video (o en el frame congelado) aísla su
  recorrido: solo se ve su línea, y aparece un botón para marcarla o quitarle
  la marca de personal.

Una misma persona puede aparecer como varias líneas cortas. No las unimos ni las
suavizamos: significa que el tracking perdió su `track_id` y es una pista para
mejorar la cámara, el encuadre o el tracking, no varios caminos reales.

Estos recorridos solo existen dentro del último análisis de esa cámara: no
identifican a la misma persona entre dos videos distintos ni entre dos
cámaras distintas.
