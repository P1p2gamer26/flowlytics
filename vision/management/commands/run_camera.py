"""Worker de una cámara: lee frames, mide, persiste. Un proceso por cámara.

Uso: python manage.py run_camera <camera_id> [--max-seconds N] [--preview]
"""
import json
import os
import time

import cv2
import numpy as np
import supervision as sv
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from analytics.avisos import reglas_de
from analytics.models import (
    CrossingWindow, Event, EventClip, HeatmapWindow, MetricWindow, Trajectory,
)
from cameras.models import Camera, CameraHealth, Recorrido
from vision.core.degradacion import ajustar_muestreo
from vision.core.detector import YoloDetector
from vision.core.geometria import pie_de_caja
from vision.core.heatmap import GridAccumulator
from vision.core.lines import LineSet
from vision.core.metrics import MetricAccumulator, TrajectoryAccumulator
from vision.core.ringbuffer import FrameRingBuffer
from vision.core.source import FrameSource, es_fuente_archivo, ruta_archivo
from vision.core.tracking import crear_tracker
from vision.core.zones import ZoneSet
from vision.pipeline import Pipeline

CLIP_SECONDS = 10


class Command(BaseCommand):
    help = "Procesa el stream de una cámara y guarda métricas agregadas."

    def add_arguments(self, parser):
        parser.add_argument("camera_id", type=int)
        parser.add_argument("--max-seconds", type=float, default=None,
                            help="Termina tras N segundos (para pruebas).")
        parser.add_argument("--window", type=int, default=60)
        parser.add_argument("--tiempo-real", action="store_true",
                            help="Archivos: procesa en cadencia real en vez de lo más rápido posible.")
        parser.add_argument("--una-pasada", action="store_true",
                            help="Archivos: procesa el video una vez y termina (default: en bucle).")
        parser.add_argument("--preview", action="store_true",
                            help="Muestra una ventana anotada. Solo para depurar en local.")

    def handle(self, *args, **opts):
        camera = Camera.objects.filter(pk=opts["camera_id"]).first()
        if camera is None:
            raise CommandError(f"No existe la cámara {opts['camera_id']}")

        zone_specs = [
            {"name": z.name, "kind": z.contexto_efectivo, "polygon": z.polygon}
            for z in camera.zones.all()
        ]
        if not zone_specs:
            raise CommandError(f"La cámara '{camera}' no tiene zonas definidas.")
        zone_kinds = {s["name"]: s["kind"] for s in zone_specs}
        line_specs = [
            {"name": ln.name, "puntos": ln.puntos, "invertir": ln.invertir}
            for ln in camera.lines.all()
        ]

        # Un archivo de video se procesa como una cámara. Por defecto rápido
        # (tiempo simulado desde el índice de frame) y en bucle; con
        # --tiempo-real se ve como un feed vivo y con --una-pasada termina.
        es_archivo = es_fuente_archivo(camera.source)
        entrada = ruta_archivo(camera.source) if es_archivo else camera.resolved_source
        tiempo_real = opts["tiempo_real"] or not es_archivo
        loop_archivo = es_archivo and not opts["una_pasada"]

        # Una sola conexión: el probe que mide la resolución se reutiliza.
        probe = cv2.VideoCapture(entrada)
        opened = probe.isOpened()
        width = int(probe.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        height = int(probe.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
        if not opened:
            probe.release()
            raise CommandError(f"No se pudo abrir la fuente: {camera.source}")

        ref_wh = (camera.frame_w, camera.frame_h) if camera.frame_w and camera.frame_h else None

        sx, sy = (ref_wh[0] / width, ref_wh[1] / height) if ref_wh else (1.0, 1.0)
        grid_acc = GridAccumulator(ref_wh or (width, height))

        zona_muerta = None
        if camera.zona_muerta:
            poly = np.array(camera.zona_muerta, dtype=float)
            if ref_wh:
                poly[:, 0] *= width / ref_wh[0]
                poly[:, 1] *= height / ref_wh[1]
            zona_muerta = sv.PolygonZone(polygon=poly.astype(int),
                                         triggering_anchors=(sv.Position.BOTTOM_CENTER,))

        _error_pendiente = [""]

        def latir(con_error=""):
            _error_pendiente[0] = con_error or _error_pendiente[0]
            CameraHealth.latir(camera, frames=frames_leidos,
                               reconexiones=fuente.reconexiones,
                               error=_error_pendiente[0],
                               fps_medido=fps_medido,
                               frames_descartados=frames_descartados)

        def aviso_de_reconexion(intento, espera, motivo):
            self.stderr.write(f"reconectando ({intento}), reintento en {espera:.0f} s: {motivo}")
            latir(f"sin señal: {motivo}")

        fuente = FrameSource(
            # El stream se resuelve en cada reconexión: la URL de YouTube caduca.
            abrir=lambda: cv2.VideoCapture(entrada if es_archivo else camera.resolved_source),
            es_archivo=es_archivo,
            loop=loop_archivo,
            captura_inicial=probe,
            max_reintentos=5 if es_archivo else None,
            al_reconectar=None if es_archivo else aviso_de_reconexion,
        )

        pipeline = Pipeline(
            detector=YoloDetector(
                settings.DETECTOR_MODEL,
                320 if not es_archivo else settings.DETECTOR_IMGSZ,
                settings.DETECTOR_DEVICE,
            ),
            zone_set=ZoneSet.from_specs(zone_specs, frame_wh=(width, height), ref_wh=ref_wh),
            zone_kinds=zone_kinds,
            accumulator=MetricAccumulator(window_seconds=opts["window"]),
            rules=reglas_de(camera.business),
            line_set=LineSet.from_specs(line_specs, frame_wh=(width, height), ref_wh=ref_wh)
                     if line_specs else None,
            tracker=crear_tracker(settings.SAMPLE_FPS,
                                  lost_track_buffer=camera.lost_track_buffer),
            zona_muerta=zona_muerta,
            trajectory_acc=TrajectoryAccumulator(window_seconds=opts["window"]),
        )
        buffer = FrameRingBuffer(seconds=CLIP_SECONDS, fps=settings.SAMPLE_FPS)
        annotator = sv.BoxAnnotator()

        # Directorio para frames en vivo
        en_vivo_dir = os.path.join(settings.MEDIA_ROOT, "en_vivo")
        os.makedirs(en_vivo_dir, exist_ok=True)
        jpg_path = os.path.join(en_vivo_dir, f"{camera.pk}.jpg")
        json_path = os.path.join(en_vivo_dir, f"{camera.pk}.json")
        ultimo_en_vivo = 0.0

        fps_objetivo = settings.SAMPLE_FPS
        base_epoch = time.time()
        started = time.monotonic()
        ultimo_latido = time.monotonic()
        indice_video = 0
        frames_leidos = 0
        pistas = []
        frames_ventana = 0
        frames_descartados = 0
        frames_descartados_ventana = 0
        fps_medido = fps_objetivo
        ventana_inicio = time.monotonic()
        salto = None
        degradada = False
        modo = "archivo" if es_archivo else "stream"
        self.stdout.write(f"Procesando '{camera}' [{modo}] a {settings.SAMPLE_FPS} FPS. "
                          f"Ctrl-C para parar.")

        try:
            while True:
                frame = fuente.leer(saltar=(salto - 1) if salto and salto > 1 else 0)
                if frame is None:
                    if es_archivo and not loop_archivo:
                        self.stdout.write("Archivo terminado.")
                        final = pipeline.cerrar()
                        if final.summary is not None:
                            MetricWindow.from_summary(camera, final.summary, zone_kinds, degradada=degradada)
                            CrossingWindow.from_summary(camera, final.summary)
                            Trajectory.from_samples(camera, final.trajectories, final.summary.ended_at)
                            grid, personas = grid_acc.cerrar()
                            if personas:
                                HeatmapWindow.from_grid(camera, final.summary.started_at,
                                                        final.summary.ended_at, grid, personas)
                            for event in final.events:
                                self._save_event(camera, event, buffer, (width, height))
                            latir()
                            self.stdout.write(
                                f"ventana final: {final.summary.occupancy_avg} "
                                f"| {len(final.events)} eventos")
                    else:
                        self.stderr.write("La fuente se cerró tras agotar los reintentos.")
                        latir("no se pudo abrir la fuente")
                    break
                indice_video += 1

                if tiempo_real:
                    timestamp = time.time()
                else:
                    timestamp = base_epoch + indice_video / (fuente.fps_archivo
                                                              or settings.SAMPLE_FPS)

                frames_leidos += 1
                frames_ventana += 1

                buffer.push(frame.copy())
                result = pipeline.process(frame, timestamp=timestamp)

                _acumular_pistas(pistas, result.detections,
                                 indice_video / (fuente.fps_archivo or fps_objetivo), sx, sy)
                _acumular_pisadas(grid_acc, result.detections, sx, sy)

                if result.summary is not None:
                    duracion_ventana = time.monotonic() - ventana_inicio
                    fps_medido = frames_ventana / duracion_ventana if duracion_ventana > 0 else fps_objetivo
                    frames_descartados = frames_descartados_ventana
                    salto = ajustar_muestreo(fps_objetivo, fps_medido)
                    degradada = salto is not None and salto > 1

                    MetricWindow.from_summary(camera, result.summary, zone_kinds, degradada=degradada)
                    CrossingWindow.from_summary(camera, result.summary)
                    Trajectory.from_samples(camera, result.trajectories, result.summary.ended_at)
                    grid, personas = grid_acc.cerrar()
                    if personas:
                        HeatmapWindow.from_grid(camera, result.summary.started_at,
                                                result.summary.ended_at, grid, personas)
                    latir()
                    for event in result.events:
                        self._save_event(camera, event, buffer, (width, height))
                    self.stdout.write(
                        f"ventana cerrada: {result.summary.occupancy_avg} "
                        f"| {len(result.events)} eventos"
                    )

                    frames_ventana = 0
                    frames_descartados_ventana = 0
                    ventana_inicio = time.monotonic()

                # latido cada ~10 s, no solo al cerrar cada ventana de 60 s
                ahora = time.monotonic()
                if ahora - ultimo_latido >= 10:
                    latir()
                    ultimo_latido = ahora

                # Escribir frame anotado y JSON en vivo cada ~2 s
                if ahora - ultimo_en_vivo >= 2.0:
                    try:
                        personas = len(result.detections)
                        frame_anotado = annotator.annotate(frame.copy(), result.detections)
                        cv2.putText(frame_anotado, f"Personas: {personas}", (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
                        tmp_jpg = jpg_path + ".tmp"
                        ok, buf = cv2.imencode(".jpg", frame_anotado)
                        if ok:
                            with open(tmp_jpg, "wb") as f:
                                f.write(buf.tobytes())
                            os.replace(tmp_jpg, jpg_path)
                        tmp_json = json_path + ".tmp"
                        with open(tmp_json, "w") as f:
                            json.dump({"personas": personas, "t": time.time()}, f)
                        os.replace(tmp_json, json_path)
                    except Exception as exc:
                        # La vista en vivo es accesoria: que no tumbe el análisis.
                        self.stderr.write(f"no se pudo escribir la vista en vivo: {exc}")
                    ultimo_en_vivo = ahora

                if opts["preview"]:
                    cv2.imshow("preview", annotator.annotate(frame.copy(), result.detections))
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

                if opts["max_seconds"] and time.monotonic() - started >= opts["max_seconds"]:
                    break
        except KeyboardInterrupt:
            self.stdout.write("Detenido por el usuario.")
        finally:
            fuente.cerrar()
            if opts["preview"]:
                cv2.destroyAllWindows()
            if pistas:
                # Una sola escritura, al final: guardar en cada frame serian miles
                # de UPDATE para un dato que solo se lee cuando la pasada termino.
                Recorrido.objects.update_or_create(camera=camera,
                                                   defaults={"pistas": pistas})
                self.stdout.write(f"recorrido guardado: {len(pistas)} instantes.")

    def _save_event(self, camera, event_data, buffer, frame_wh):
        from django.core.files.base import ContentFile
        from django.utils import timezone

        event = Event.objects.create(
            camera=camera,
            kind=event_data["kind"],
            zone_name=event_data["zone_name"],
            value=event_data["value"],
            occurred_at=timezone.now(),
        )
        from analytics.notifier import notificar_evento
        try:
            notificar_evento(event)
        except Exception as exc:
            self.stderr.write(f"no se pudo notificar el evento: {exc}")

        frames = buffer.frames()
        if not frames:
            return

        import tempfile
        from pathlib import Path

        tmp = Path(tempfile.gettempdir()) / f"clip_{event.pk}.mp4"
        # avc1 (H.264) y no mp4v: los clips se revisan en el navegador, y
        # ningún navegador decodifica MPEG-4 Part 2.
        writer = cv2.VideoWriter(str(tmp), cv2.VideoWriter_fourcc(*"avc1"),
                                 settings.SAMPLE_FPS, frame_wh)
        for f in frames:
            writer.write(f)
        writer.release()
        if not tmp.exists():
            # OpenCV sin codificador H.264 (p. ej. la VM) no escribe nada: el
            # evento ya quedó guardado, solo se pierde el clip. Antes tumbaba el worker.
            self.stderr.write(f"evento {event.pk} sin clip: no se pudo escribir H.264")
            return

        clip = EventClip(event=event, expires_at=EventClip.default_expiry())
        clip.file.save(f"event_{event.pk}.mp4", ContentFile(tmp.read_bytes()), save=True)
        tmp.unlink(missing_ok=True)


def _acumular_pisadas(grid_acc, detecciones, sx, sy):
    """Añade el pie de cada persona rastreada de este cuadro a la rejilla,
    escalado a la resolución de referencia de la cámara."""
    ids = getattr(detecciones, "tracker_id", None)
    if ids is None or len(detecciones) == 0:
        return
    pies = []
    for caja, tid in zip(detecciones.xyxy, ids):
        if tid is None:
            continue
        x, y = pie_de_caja(caja)
        pies.append((int(tid), (x * sx, y * sy)))
    if pies:
        grid_acc.observe(pies)


def _acumular_pistas(pistas, detecciones, segundo, sx=1.0, sy=1.0):
    """Anade el instante actual si hay alguien rastreado.

    Solo se guardan detecciones CON `tracker_id`: sin identidad no se puede decir
    "esta persona lleva tres minutos", que es para lo que existe esto. Las
    coordenadas se escalan a la resolucion DE REFERENCIA de la camara
    (`sx, sy`, las mismas que ya usa `_acumular_pisadas` para el mapa de calor y
    `ZoneSet`/`LineSet` para zonas y lineas) para que el frontend, que dibuja
    con esa misma resolucion como `viewBox`, reciba cajas en su misma escala
    aunque el video analizado tenga otra resolucion nativa. Van a entero — el
    pixel de mas no aporta y el JSON pesa la mitad.
    """
    ids = getattr(detecciones, "tracker_id", None)
    if ids is None or len(detecciones) == 0:
        return
    cajas = [
        {"id": int(tid), "xyxy": [int(caja[0] * sx), int(caja[1] * sy),
                                  int(caja[2] * sx), int(caja[3] * sy)]}
        for caja, tid in zip(detecciones.xyxy, ids) if tid is not None
    ]
    if cajas:
        pistas.append({"t": round(float(segundo), 2), "cajas": cajas})
