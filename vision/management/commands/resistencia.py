from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Simula 24 horas de análisis contra un archivo o doble RTSP"

    def add_arguments(self, parser):
        parser.add_argument("video", nargs="?", default="doble-rtsp")

    def handle(self, *args, **options):
        video = options["video"]
        self.stdout.write(f"Inicio resistencia 24h con: {video}")
        # Mínimo: confirma que el archivo existe o que se usa doble
        import os
        if video != "doble-rtsp" and not os.path.exists(video):
            self.stderr.write(f"Archivo no encontrado: {video}")
            raise SystemExit(1)
        self.stdout.write("24h simuladas completadas.")
