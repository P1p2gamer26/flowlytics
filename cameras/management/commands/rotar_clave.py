from django.core.management.base import BaseCommand

from cameras.models import Camera, clave_desde_secreto
from cameras.rotacion import rotar


class Command(BaseCommand):
    help = ("Re-cifra las credenciales de cámara con un SECRET_KEY nuevo. "
            "Correr ANTES de cambiar el secreto en .env.")

    def add_arguments(self, parser):
        parser.add_argument("--secreto-viejo", required=True)
        parser.add_argument("--secreto-nuevo", required=True)

    def handle(self, *args, **opts):
        rotar(Camera.objects.all(),
              clave_desde_secreto(opts["secreto_viejo"]),
              clave_desde_secreto(opts["secreto_nuevo"]))
        self.stdout.write(self.style.SUCCESS(
            "Credenciales re-cifradas. Ahora sí cambia DJANGO_SECRET_KEY en .env."))
