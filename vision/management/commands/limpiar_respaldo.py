import os, re, glob
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from analytics.models import JobRun

class Command(BaseCommand):
    help = "Elimina respaldos antiguos según retención de días"

    def add_arguments(self, parser):
        parser.add_argument("--dias", type=int, default=getattr(settings, "RETENCION_RESPALDO_DIAS", 30))

    def handle(self, *args, **options):
        dias = options["dias"]
        backup_dir = "backups"
        borrados = 0
        conservados = 0
        patron = re.compile(r"respaldo_(\d{4}-\d{2}-\d{2})_(\d{6})\.tar\.gz")
        hoy = datetime.now()
        for ruta in glob.glob(os.path.join(backup_dir, "respaldo_*.tar.gz")):
            nombre = os.path.basename(ruta)
            m = patron.match(nombre)
            if not m:
                continue
            fecha_archivo = datetime.strptime(m.group(1), "%Y-%m-%d")
            if (hoy - fecha_archivo).days > dias:
                os.remove(ruta)
                borrados += 1
            else:
                conservados += 1
        detalle = f"borrados={borrados} conservados={conservados} retencion={dias}"
        JobRun.marcar("limpieza_respaldo", ok=True, detalle=detalle)
        self.stdout.write(detalle)