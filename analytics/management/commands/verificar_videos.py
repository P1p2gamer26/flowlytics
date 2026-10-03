"""Revisa que todos los videos de cámaras de archivo sean reproducibles."""
from django.core.management.base import BaseCommand

from cameras.models import Camera
from vision.core.codecs import es_h264
from vision.core.source import es_fuente_archivo, ruta_archivo


class Command(BaseCommand):
    help = "Falla si alguna cámara apunta a un video que el navegador no puede abrir."

    def handle(self, *args, **opts):
        malos = []
        for camera in Camera.objects.all():
            if not es_fuente_archivo(camera.source):
                continue
            ruta = ruta_archivo(camera.source)
            if es_h264(ruta):
                self.stdout.write(f"ok    {camera.name}: {ruta}")
            else:
                malos.append((camera.name, ruta))
                self.stdout.write(self.style.ERROR(f"ROTO  {camera.name}: {ruta}"))

        if malos:
            self.stderr.write(
                f"\n{len(malos)} video(s) no son H.264: el navegador no los "
                "reproducirá. Corre `python demo/transcodificar_videos.py`."
            )
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("Todos los videos son reproducibles."))
