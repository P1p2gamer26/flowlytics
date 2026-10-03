"""Reporte de precisión: corre el banco de video contra el conteo de referencia
anotado a mano y escribe una tabla con el error %.

`medir_video` es lo único que toca OpenCV/YOLO y NO se ejercita en los tests: se
inyecta un doble. La comparación vive en analytics.precision, ya probada.
"""
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from analytics.precision import cuerpo_para_el_documento, generar_reporte, insertar_entre_marcas


def medir_video(entry, base_dir):
    """Corre el pipeline una pasada sobre el video del banco y devuelve
    {'entradas', 'salidas', 'aforo_max'} medidos. Requiere el video real y YOLO."""
    import cv2

    from analytics.precision import medir_desde_ventanas
    from vision.core.detector import YoloDetector
    from vision.core.lines import LineSet
    from vision.core.metrics import MetricAccumulator
    from vision.core.tracking import crear_tracker
    from vision.core.zones import ZoneSet
    from vision.pipeline import Pipeline

    ruta = Path(base_dir) / "demo" / "videos" / entry["ruta"]
    cap = cv2.VideoCapture(str(ruta))
    if not cap.isOpened():
        raise FileNotFoundError(f"No se pudo abrir {ruta}. ¿Está el video en demo/videos/?")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or entry.get("ancho", 640)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or entry.get("alto", 480)
    fps = cap.get(cv2.CAP_PROP_FPS) or entry.get("fps", 25.0)

    ref_wh = (entry.get("ancho"), entry.get("alto")) if entry.get("ancho") else None
    line_specs = entry.get("lineas", [])
    # Conversión mínima: referencia usa `lineas` con puntos de inicio/fin,
    # LineSet espera specs con `puntos`.
    line_specs_convertidas = []
    for spec in line_specs:
        line_specs_convertidas.append({
            "name": spec.get("nombre"),
            "puntos": (spec.get("punto_inicio"), spec.get("punto_fin")),
            "invertir": spec.get("invertir", False),
        })
    line_specs = line_specs_convertidas
    # El frame entero como zona única: sin ninguna zona el acumulador no reporta
    # ocupación y aforo_max salía 0 contra cualquier anotación. "Aforo" aquí es
    # cuántas personas se ven a la vez en el cuadro, que es lo que se anota a mano.
    marco = [[0, 0], [width, 0], [width, height], [0, height]]
    pipeline = Pipeline(
        detector=YoloDetector(settings.DETECTOR_MODEL, settings.DETECTOR_IMGSZ,
                              settings.DETECTOR_DEVICE),
        zone_set=ZoneSet.from_specs([{"name": "todo", "polygon": marco}],
                                    frame_wh=(width, height)),
        zone_kinds={},
        accumulator=MetricAccumulator(window_seconds=10 ** 9),   # una sola ventana: todo el video
        rules=[],
        line_set=LineSet.from_specs(line_specs, frame_wh=(width, height), ref_wh=ref_wh)
                 if line_specs else None,
        tracker=crear_tracker(fps),
    )

    ventanas = []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        idx += 1
        resultado = pipeline.process(frame, timestamp=idx / fps)
        if resultado.summary is not None:
            ventanas.append(resultado.summary)
    cap.release()

    final = pipeline.cerrar()          # el archivo se acabó: cerrar la ventana en curso
    if final.summary is not None:
        ventanas.append(final.summary)
    return medir_desde_ventanas(ventanas)


class Command(BaseCommand):
    help = "Compara el banco de video con el conteo de referencia y escribe el error %."

    def add_arguments(self, parser):
        parser.add_argument("--referencia", default=str(Path(settings.BASE_DIR) / "demo" / "referencia.json"))
        parser.add_argument("--salida", default=str(Path(settings.BASE_DIR) / "demo" / "reporte_precision.md"))
        parser.add_argument("--publicar", action="store_true",
                            help="Además, mete el reporte en docs/tecnico.md entre las marcas.")
        parser.add_argument("--doc", default=str(Path(settings.BASE_DIR) / "docs" / "tecnico.md"))

    def handle(self, *args, **opts):
        referencia = json.loads(Path(opts["referencia"]).read_text(encoding="utf-8"))
        texto, resultados = generar_reporte(
            referencia, medidor=lambda entry: medir_video(entry, settings.BASE_DIR))
        # encoding explícito: el reporte lleva acentos y en Windows el default es
        # cp1252, que lo deja ilegible para quien luego lo abre como UTF-8.
        Path(opts["salida"]).write_text(texto, encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(
            f"{len(resultados)} videos evaluados. Reporte en {opts['salida']}."))

        if not opts.get("publicar"):
            return

        doc = Path(opts["doc"])
        sello = (f"_Generado el {timezone.localdate():%Y-%m-%d} con "
                 "`manage.py reporte_precision --publicar`. No editar a mano: "
                 "se sobrescribe._")
        # insertar_entre_marcas revienta antes de escribir si faltan las marcas
        nuevo = insertar_entre_marcas(
            doc.read_text(encoding="utf-8"),
            sello + "\n\n" + cuerpo_para_el_documento(texto))
        doc.write_text(nuevo, encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Publicado en {doc}."))
        if not resultados:
            self.stdout.write(
                "Ningún video anotado: lo publicado dice que no hay medición todavía. "
                "Para que haya un número: manage.py anotar_referencia <video> --entradas N.")
