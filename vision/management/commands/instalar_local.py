from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Verifica que el entorno está listo para instalar en un local real"

    def handle(self, *args, **options):
        import os
        if not os.path.exists(".env"):
            self.stderr.write("No se encontró .env; crear con la URL de la cámara")
            raise SystemExit(1)
        self.stdout.write("Entorno listo para instalación local.")
        raise SystemExit(0)
