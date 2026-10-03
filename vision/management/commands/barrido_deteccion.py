"""Barre `imgsz` y `SAMPLE_FPS` sobre un video y dice que cuesta cada combinacion.

La pregunta que responde no es "cual detecta mas", que siempre es el mas caro,
sino "cual detecta mas de lo que esta VM puede sostener en vivo". Un ajuste que
no aguanta el tiempo real no sirve para una camara colgada en un local, que es a
donde va esto (docs/NORTE.md).
"""
import time
from itertools import product
from pathlib import Path

import cv2

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from vision.core.detector import YoloDetector


def aguanta_en_vivo(segundos_por_frame: float, fps: float) -> bool:
    """Con `fps` muestras por segundo hay 1/fps segundos para procesar cada una."""
    if segundos_por_frame <= 0:
        return True
    return segundos_por_frame <= (1.0 / fps)


def tabla(filas) -> str:
    cab = "| imgsz | FPS | personas/frame | s/frame | \u00bfen vivo? |"
    sep = "|---|---|---|---|---|"
    cuerpo = [
        f"| {f['imgsz']} | {f['fps']} | {f['personas_por_frame']:.2f} | "
        f"{f['segundos_por_frame']:.3f} | "
        f"{'si' if f['aguanta_en_vivo'] else 'NO aguanta'} |"
        for f in sorted(filas, key=lambda f: -f["personas_por_frame"])
    ]
    return "\n".join([cab, sep, *cuerpo])


class Command(BaseCommand):
    help = "Barre combinaciones de imgsz y FPS sobre un video y mide cual aguanta en vivo."

    def add_arguments(self, parser):
        parser.add_argument("video", help="Ruta al archivo de video.")
        parser.add_argument("--imgsz", default="416,640",
                            help="Tamaños de imagen separados por coma (default 416,640).")
        parser.add_argument("--fps", default="2,6,12",
                            help="FPS de muestreo separados por coma (default 2,6,12).")
        parser.add_argument("--max-segundos", type=float, default=120,
                            help="Segundos de video a recorrer por combinacion (default 120).")

    def handle(self, *args, **opts):
        video_path = Path(opts["video"])
        if not video_path.is_file():
            raise CommandError(f"No existe el archivo {video_path}.")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            cap.release()
            raise CommandError(f"OpenCV no pudo abrir {video_path}.")
        fps_video = cap.get(cv2.CAP_PROP_FPS) or 1.0
        cap.release()

        tamanios = [int(s.strip()) for s in opts["imgsz"].split(",") if s.strip()]
        muestreos = [float(f.strip()) for f in opts["fps"].split(",") if f.strip()]

        self.stdout.write(f"Video: {video_path} ({fps_video:.1f} fps)\n")
        self.stdout.write(f"Combinations: {len(tamanios)} imgsz x {len(muestreos)} fps = "
                          f"{len(tamanios) * len(muestreos)}\n")

        filas = []
        for imgsz, fps_val in product(tamanios, muestreos):
            tiempos, personas = self._medir(video_path, imgsz, fps_val,
                                             opts["max_segundos"], fps_video)
            if not tiempos:
                self.stdout.write(self.style.WARNING(
                    f"  {imgsz}/{fps_val}: no hubo frames medibles"))
                continue
            seg_por_frame = sum(tiempos) / len(tiempos)
            personas_frame = sum(personas) / len(personas) if personas else 0.0
            filas.append({
                "imgsz": imgsz,
                "fps": fps_val,
                "personas_por_frame": personas_frame,
                "segundos_por_frame": seg_por_frame,
                "aguanta_en_vivo": aguanta_en_vivo(seg_por_frame, fps_val),
            })
            self.stdout.write(f"  {imgsz}/{fps_val}: {personas_frame:.2f} p/f, "
                              f"{seg_por_frame:.3f}s/f, "
                              f"{'OK' if filas[-1]['aguanta_en_vivo'] else 'NO aguanta'}")

        self.stdout.write("\n" + tabla(filas))

    def _medir(self, video_path, imgsz, fps_val, max_segundos, fps_video):
        detector = YoloDetector(settings.DETECTOR_MODEL, imgsz,
                                settings.DETECTOR_DEVICE)
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return [], []
        try:
            intervalo = 1.0 / fps_val
            tiempos = []
            personas = []
            frame_idx = 0
            ultimo_muestreo = None
            inicio = time.perf_counter()
            max_frames = int(max_segundos * fps_video)

            while frame_idx < max_frames:
                ok, frame = cap.read()
                if not ok:
                    break
                ts = frame_idx / fps_video
                if ultimo_muestreo is not None and ts - ultimo_muestreo < intervalo:
                    frame_idx += 1
                    continue
                ultimo_muestreo = ts
                t0 = time.perf_counter()
                dets = detector.detect(frame)
                tiempos.append(time.perf_counter() - t0)
                personas.append(len(dets))
                if time.perf_counter() - inicio > max_segundos:
                    break
                frame_idx += 1
        finally:
            cap.release()
        return tiempos, personas
