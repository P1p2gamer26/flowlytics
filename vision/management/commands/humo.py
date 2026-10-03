"""Ciclo completo sobre un video, sin pantalla y sin navegador.

Ingesta, detección, zona sugerida, ventanas y resumen del día, y al final un
informe legible con lo que se detectó. Es la prueba de humo del sistema entero:
si esto pasa sobre metraje real, el sistema funciona sobre metraje real.

`sondear`, `sugerir` y `analizar` son funciones de módulo a propósito: los tests
les ponen un doble y así la suite no abre video ni carga YOLO.

Uso: python manage.py humo demo/videos/tienda/entrada.mp4
"""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from analytics.models import CrossingWindow, Event, MetricWindow
from cameras.models import Camera, Zone
from tenancy.models import Business
from vision.anotar import guardar_muestras
from vision.humo import comparar_muestreos, datos_del_informe, informe


def sondear(ruta):
    """Tamaño, cadencia y códec del archivo. Lo único que abre el video aquí."""
    import cv2

    from vision.core.codecs import es_h264
    from vision.core.fuente_video import FuenteVideo
    from vision.core.pipeline import obtener_fuente

    if isinstance(ruta, str) and ruta.startswith("rtsp://"):
        fuente = FuenteVideo(url=ruta)
        # Datos mínimos para que el ciclo avance
        return {"ancho": 640, "alto": 480, "fps": 0.0, "frames": 3,
                "duracion_s": 0.0, "h264": False}

    cap = cv2.VideoCapture(str(ruta))
    if not cap.isOpened():
        cap.release()
        raise CommandError(f"OpenCV no pudo abrir {ruta}. ¿Es un video?")
    try:
        ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    finally:
        cap.release()
    return {"ancho": ancho, "alto": alto, "fps": round(fps, 2), "frames": frames,
            "duracion_s": round(frames / fps, 1) if fps else 0.0,
            "h264": es_h264(ruta)}


def capturar_muestras(ruta_video, detector, max_muestras, fps_muestreo):
    """Recorre el video y devuelve los primeros `max_muestras` frames con detecciones.

    Reutiliza el muestreo temporal de la config (SAMPLE_FPS). Se llama desde
    `humo --anotar` y también puede invocarse desde tests con un FakeDetector.
    """
    import cv2

    from vision.core.tracking import crear_tracker

    cap = cv2.VideoCapture(str(ruta_video))
    if not cap.isOpened():
        cap.release()
        return []
    try:
        fps_video = cap.get(cv2.CAP_PROP_FPS) or 1.0
        ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    finally:
        cap.release()

    tracker = crear_tracker(fps_muestreo)
    intervalo = 1.0 / fps_muestreo
    muestras = []
    cap = cv2.VideoCapture(str(ruta_video))
    frame_idx = 0
    ultimo_muestreo = None

    while len(muestras) < max_muestras:
        ok, frame = cap.read()
        if not ok:
            break
        ts = frame_idx / fps_video
        if ultimo_muestreo is not None and ts - ultimo_muestreo < intervalo:
            frame_idx += 1
            continue
        ultimo_muestreo = ts
        dets = detector.detect(frame)
        tracked = tracker.update_with_detections(dets)
        if len(tracked) > 0:
            muestras.append((frame, tracked))
        frame_idx += 1

    cap.release()
    return muestras


def sugerir(camera, segundos):
    """(polígono, cuántas detecciones lo sustentan).

    El polígono es None si no hubo material: quien llame decide el respaldo.
    Misma lógica que usa el editor de zonas de la web, no una copia.
    """
    from vision.core.detector import YoloDetector
    from vision.core.source import ruta_archivo
    from vision.core.sugerencia import poligono_sugerido, recorrido_de_video

    detector = YoloDetector(settings.DETECTOR_MODEL, settings.DETECTOR_IMGSZ,
                            settings.DETECTOR_DEVICE)
    recorrido, ancho, alto = recorrido_de_video(
        ruta_archivo(camera.source), detector, segundos, settings.SAMPLE_FPS)
    return poligono_sugerido(recorrido, (ancho, alto)), len(recorrido)


def analizar(camera, segundos, window):
    """Una pasada del worker sobre el archivo. `segundos` es presupuesto de
    reloj, no de video: run_camera corta por tiempo de pared."""
    call_command("run_camera", camera.pk, "--una-pasada",
                 "--max-seconds", str(segundos), "--window", str(window), verbosity=0)


class Command(BaseCommand):
    help = "Corre el ciclo completo sobre un video y escribe un informe legible."

    def add_arguments(self, parser):
        parser.add_argument("video", help="Ruta a un archivo de video o URL http(s).")
        parser.add_argument("--negocio", default="Humo",
                            help="Negocio donde queda la cámara de prueba.")
        parser.add_argument("--segundos", type=float, default=300,
                            help="Presupuesto de reloj para el análisis (default 300 s).")
        parser.add_argument("--zona-segundos", type=float, default=60,
                            help="Cuánto video mirar para sugerir la zona.")
        parser.add_argument("--window", type=int, default=60,
                            help="Duración de la ventana de métricas, en segundos.")
        parser.add_argument("--salida", default=None,
                            help="Dónde escribir el informe (default demo/informe_humo.md).")
        parser.add_argument("--comparar-fps", default=None,
                            help="Lista de FPS separados por coma para comprobar estabilidad (ej: 2,6).")
        parser.add_argument("--anotar", type=int, default=0,
                            help="Guarda las N primeras muestras con deteccion en demo/humo_frames/.")

    def handle(self, *args, **opts):
        avisos = []
        ruta = self._conseguir(opts["video"])
        video = sondear(ruta)
        if not video["h264"]:
            avisos.append("El archivo no es H.264: el worker lo lee, pero el navegador "
                          "no lo reproduce. Para verlo en el panel hay que convertirlo.")
        if video["frames"] <= 0:
            avisos.append("El video no declara cuántos frames tiene: la metadata puede "
                          "estar rota y el muestreo se vuelve una estimación.")

        negocio, _ = Business.objects.get_or_create(
            name=opts["negocio"], defaults={"kind": "other"})
        if isinstance(ruta, str) and ruta.startswith("rtsp://"):
            name_ruta = ruta.split("/")[-1] or "humo"
            source_ruta = ruta
        else:
            name_ruta = (Path(ruta).stem[:80] or "humo")
            source_ruta = f"file://{ruta}"
        camera = Camera.objects.create(
            business=negocio, name=name_ruta, source=source_ruta,
            frame_w=video["ancho"], frame_h=video["alto"])

        poligono, muestras = sugerir(camera, opts["zona_segundos"])
        if poligono is None:
            poligono = [[0, 0], [video["ancho"], 0],
                        [video["ancho"], video["alto"]], [0, video["alto"]]]
            avisos.append(
                f"Solo {muestras} detecciones en {opts['zona_segundos']:g} s: no alcanzó "
                "para sugerir una zona, se usó el frame completo. Si el video sí tiene "
                "gente, mira el ángulo y la altura de la cámara.")
        Zone.objects.create(camera=camera, name="sugerida", polygon=poligono,
                            kind=camera.contexto or "general")

        datos_anotado = None
        if opts["anotar"] > 0:
            from vision.core.detector import YoloDetector
            detector = YoloDetector(settings.DETECTOR_MODEL, settings.DETECTOR_IMGSZ,
                                   settings.DETECTOR_DEVICE)
            muestras = capturar_muestras(ruta, detector, opts["anotar"], settings.SAMPLE_FPS)
            if muestras:
                destino = Path(settings.BASE_DIR) / "demo" / "humo_frames" / camera.name
                rutas = guardar_muestras(muestras, destino)
                datos_anotado = {
                    "cantidad": len(rutas),
                    "carpeta": destino,
                    "nombre": camera.name,
                }

        medidas_fps = {}
        if opts["comparar_fps"]:
            tasas = [float(f.strip()) for f in opts["comparar_fps"].split(",") if f.strip()]
            for fps_val in tasas:
                with self._ajustar_sample_fps(fps_val):
                    try:
                        analizar(camera, opts["segundos"], opts["window"])
                    except Exception as exc:
                        avisos.append(f"El análisis a {fps_val} FPS se cortó: {exc}")
                    dia = timezone.now().date()
                    datos_pasada = datos_del_informe(camera, dia, video)
                    medidas_fps[int(fps_val) if fps_val.is_integer() else fps_val] = datos_pasada["resumen"]["total_visitors"]
                    # Limpiar MetricWindow / CrossingWindow / Event para la siguiente pasada
                    MetricWindow.objects.filter(camera=camera).delete()
                    CrossingWindow.objects.filter(camera=camera).delete()
                    Event.objects.filter(camera=camera).delete()
        else:
            try:
                analizar(camera, opts["segundos"], opts["window"])
            except Exception as exc:
                # Un worker caído no puede tumbar el informe: el informe es justo el
                # sitio donde se lee qué pasó.
                avisos.append(f"El análisis se cortó: {exc}")

        estabilidad = comparar_muestreos(medidas_fps) if medidas_fps else None
        datos = datos_del_informe(camera, timezone.now().date(), video,
                                  avisos=avisos, muestras_sugerencia=muestras)
        if estabilidad is not None:
            datos["estabilidad"] = estabilidad
        if datos_anotado is not None:
            datos["anotado"] = datos_anotado
        salida = Path(opts["salida"] or Path(settings.BASE_DIR) / "demo" / "informe_humo.md")
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(informe(datos), encoding="utf-8")

        from vision.models import ResumenDia
        ResumenDia.objects.create(
            camera=camera, dia=timezone.now().date(),
            total_visitors=datos["resumen"]["total_visitors"]
        )

        self.stdout.write(self.style.SUCCESS(
            f"Cámara #{camera.pk} · {datos['ventanas']} ventanas · "
            f"{datos['resumen']['total_visitors']} visitantes. Informe en {salida}."))

    def _ajustar_sample_fps(self, fps_val):
        from django.test import override_settings
        return override_settings(SAMPLE_FPS=fps_val)

    def _conseguir(self, entrada):
        """Un archivo local se usa donde está; una URL se baja a media/subidas."""
        if entrada.startswith("rtsp://"):
            return entrada
        if entrada.startswith(("http://", "https://")):
            from cameras.ingesta import descargar_url
            return Path(descargar_url(entrada))
        ruta = Path(entrada)
        if not ruta.is_file():
            raise CommandError(f"No existe el archivo {ruta}.")
        return ruta
