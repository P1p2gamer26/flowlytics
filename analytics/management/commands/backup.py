"""pg_dump comprimido + poda de retención. Marca JobRun('backup')."""
import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from analytics.backups import elegir_para_borrar
from analytics.models import JobRun

DESTINO = Path(settings.BASE_DIR) / "backups"


class Command(BaseCommand):
    help = "Respaldo comprimido de la base y poda según retención."

    def handle(self, *args, **opts):
        DESTINO.mkdir(exist_ok=True)
        marca = datetime.now().strftime("%Y%m%dT%H%M%S")
        salida = DESTINO / f"backup-{marca}.sql.gz"
        db = settings.DATABASES["default"]

        with open(salida, "wb") as f:
            dump = subprocess.Popen(
                ["pg_dump", "-h", db["HOST"], "-U", db["USER"], db["NAME"]],
                stdout=subprocess.PIPE,
                env={"PGPASSWORD": db["PASSWORD"], "PATH": "/usr/bin:/bin"},
            )
            gzip = subprocess.Popen(["gzip"], stdin=dump.stdout, stdout=f)
            dump.stdout.close()
            gzip.communicate()

        nombres = [p.name for p in DESTINO.glob("backup-*.sql.gz")]
        for n in elegir_para_borrar(nombres):
            (DESTINO / n).unlink()

        JobRun.marcar("backup", detalle=salida.name)
        self.stdout.write(self.style.SUCCESS(f"Respaldo {salida.name}."))
