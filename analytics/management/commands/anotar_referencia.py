"""Prepara (o completa) la entrada de un video en demo/referencia.json.

Anotar era editar JSON a mano, y ahí se cuelan los errores caros: `ancho` y
`alto` escalan la línea de conteo (LineSet.from_specs los recibe como ref_wh),
así que copiarlos mal mueve la línea y el error medido deja de ser el del video.
Esas claves las saca el comando del archivo; el conteo a mano sigue siendo a
mano, porque nadie más lo puede saber.

    .venv/bin/python manage.py anotar_referencia demo/videos/cctv/tienda_iprox.mp4 \
        --ruta tienda/entrada.mp4 --entradas 37 --salidas 35 --aforo-max 6
"""
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from analytics.precision import anotar
from vision.management.commands.humo import sondear


class Command(BaseCommand):
    help = "Anota un video del banco en demo/referencia.json (sondea el archivo por ti)."

    def add_arguments(self, parser):
        parser.add_argument("video", help="Ruta al archivo de video.")
        parser.add_argument("--ruta", default=None,
                            help="Ruta relativa a demo/videos/ con la que se guarda "
                                 "(default: la que se deduzca del archivo).")
        parser.add_argument("--contexto", default=None, help="tienda, calle, ...")
        parser.add_argument("--origen", default=None, help="De dónde salió el video.")
        parser.add_argument("--notas", default=None)
        parser.add_argument("--entradas", type=int, default=None,
                            help="Personas que entraron, contadas a mano.")
        parser.add_argument("--salidas", type=int, default=None)
        parser.add_argument("--aforo-max", type=int, default=None,
                            help="Máximo de personas simultáneas, contadas a mano.")
        parser.add_argument("--referencia",
                            default=str(Path(settings.BASE_DIR) / "demo" / "referencia.json"))

    def handle(self, *args, **opts):
        video = Path(opts["video"])
        if not video.is_file():
            raise CommandError(f"No existe el archivo {video}.")

        datos = sondear(video)
        if not datos["h264"]:
            self.stdout.write(self.style.WARNING(
                "El video no es H264: el worker lo lee, pero el navegador no lo "
                "reproduce y el editor de zonas se queda en negro. "
                "python demo/transcodificar_videos.py lo convierte."))

        entry = {"ruta": opts["ruta"] or self._ruta_relativa(video),
                 "ancho": datos["ancho"], "alto": datos["alto"],
                 "fps": datos["fps"], "duracion_s": datos["duracion_s"]}
        for clave in ("contexto", "origen", "notas", "entradas", "salidas", "aforo_max"):
            if opts.get(clave) is not None:
                entry[clave] = opts[clave]

        ruta_ref = Path(opts["referencia"])
        referencia = json.loads(ruta_ref.read_text(encoding="utf-8")) \
            if ruta_ref.exists() else {"videos": []}
        anotar(referencia, entry)
        # ensure_ascii=False deja acentos en el JSON, asi que el encoding no es
        # opcional: en Windows el default es cp1252 y el archivo queda ilegible.
        ruta_ref.write_text(json.dumps(referencia, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")

        falta = [c for c in ("entradas", "salidas") if entry.get(c) is None]
        self.stdout.write(self.style.SUCCESS(f"{entry['ruta']} anotado en {ruta_ref}."))
        if falta:
            self.stdout.write(
                f"Falta el conteo a mano ({', '.join(falta)}): mira el video, cuenta, y "
                f"vuelve a correr esto con --{falta[0]} N. Sin eso el video se omite "
                "del reporte de precisión.")

    def _ruta_relativa(self, video):
        """demo/videos/cctv/a.mp4 -> cctv/a.mp4; cualquier otra ruta, el nombre."""
        base = Path(settings.BASE_DIR) / "demo" / "videos"
        try:
            return str(video.resolve().relative_to(base.resolve()))
        except ValueError:
            return video.name
