"""Diagnóstico con números de cómo se generan las cajas sobre un video real.

`medir_video` es lo único que toca OpenCV/YOLO y no se ejercita en los tests,
igual que `reporte_precision.medir_video`. `informe_de_diagnostico` es pura:
arma el texto a partir de un diagnóstico ya calculado.
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from vision.core.diagnostico_cajas import diagnosticar_pistas

UMBRAL_SALTO_DEFECTO = 200  # px de salto entre instantes consecutivos de un track_id


def medir_video(ruta, ref_wh=None):
    """Corre detector + tracker una pasada real y devuelve (pistas, frame_wh)."""
    import cv2

    from vision.core.detector import YoloDetector
    from vision.core.tracking import crear_tracker

    cap = cv2.VideoCapture(str(ruta))
    if not cap.isOpened():
        raise FileNotFoundError(f"No se pudo abrir {ruta}")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

    detector = YoloDetector(settings.DETECTOR_MODEL, settings.DETECTOR_IMGSZ,
                            settings.DETECTOR_DEVICE)
    tracker = crear_tracker(fps)
    pistas, idx = [], 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        idx += 1
        detecciones = tracker.update_with_detections(detector.detect(frame))
        ids = getattr(detecciones, "tracker_id", None)
        if ids is not None and len(detecciones):
            cajas = [{"id": int(tid), "xyxy": [int(v) for v in caja]}
                     for caja, tid in zip(detecciones.xyxy, ids) if tid is not None]
            if cajas:
                pistas.append({"t": round(idx / fps, 2), "cajas": cajas})
    cap.release()
    return pistas, (width, height)


def informe_de_diagnostico(nombre_video, diagnostico, umbral_salto=UMBRAL_SALTO_DEFECTO):
    lineas = [f"# Diagnóstico de cajas — {nombre_video}", ""]
    if diagnostico["necesita_reescalar"]:
        lineas.append("- La resolución analizada difiere de la de referencia: "
                      "necesita reescalarse.")
    else:
        lineas.append("- La resolución analizada coincide con la de referencia: "
                      "no necesita reescalarse.")

    fuera = diagnostico["cajas_fuera_de_referencia"]
    lineas.append(f"- {fuera} caja(s) quedarían fuera del cuadro de referencia."
                  if fuera else "- ninguna caja queda fuera del cuadro de referencia.")

    sospechosos = {tid: s for tid, s in diagnostico["salto_maximo_por_track"].items()
                   if s >= umbral_salto}
    if sospechosos:
        lineas.append("- Saltos sospechosos (posible id reasignado o caja atrasada):")
        for tid, salto in sorted(sospechosos.items()):
            lineas.append(f"  - track {tid}: {salto:.0f} px entre instantes consecutivos.")
    else:
        lineas.append("- Ningún track salta más de "
                      f"{umbral_salto} px entre instantes consecutivos.")
    return "\n".join(lineas) + "\n"


class Command(BaseCommand):
    help = "Corre el pipeline real sobre un video y mide si las cajas se generan bien."

    def add_arguments(self, parser):
        parser.add_argument("video")
        parser.add_argument("--ref-ancho", type=int, default=None)
        parser.add_argument("--ref-alto", type=int, default=None)
        parser.add_argument("--salida", default=None)

    def handle(self, *args, **opts):
        ruta = Path(opts["video"])
        if not ruta.exists():
            raise CommandError(f"No existe el video: {ruta}")

        pistas, frame_wh = medir_video(ruta)
        ref_wh = ((opts["ref_ancho"], opts["ref_alto"])
                  if opts["ref_ancho"] and opts["ref_alto"] else frame_wh)
        diagnostico = diagnosticar_pistas(pistas, frame_wh, ref_wh)
        texto = informe_de_diagnostico(ruta.name, diagnostico)

        salida = Path(opts["salida"] or
                      Path(settings.BASE_DIR) / "demo" / f"diagnostico_cajas_{ruta.stem}.md")
        salida.write_text(texto, encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Diagnóstico escrito en {salida}."))
