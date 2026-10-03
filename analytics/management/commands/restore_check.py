"""Restaura el último dump en una base temporal y corre un conteo de sanidad.
Marca JobRun('restore_check', ok=...). Envuelve psql; no se ejecuta en tests."""
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from analytics.models import JobRun

DESTINO = Path(settings.BASE_DIR) / "backups"
BASE_TMP = "vision_restore_check"


class Command(BaseCommand):
    help = "Verifica que el último respaldo se puede restaurar."

    def handle(self, *args, **opts):
        dumps = sorted(DESTINO.glob("backup-*.sql.gz"))
        if not dumps:
            JobRun.marcar("restore_check", ok=False, detalle="no hay respaldos")
            self.stderr.write("No hay respaldos que verificar.")
            return
        ultimo = dumps[-1]
        db = settings.DATABASES["default"]
        env = {"PGPASSWORD": db["PASSWORD"], "PATH": "/usr/bin:/bin"}
        base = ["-h", db["HOST"], "-U", db["USER"]]
        try:
            subprocess.run(["dropdb", "--if-exists", *base, BASE_TMP], env=env, check=True)
            subprocess.run(["createdb", *base, BASE_TMP], env=env, check=True)
            restore = f"gunzip -c {ultimo} | psql {' '.join(base)} {BASE_TMP}"
            subprocess.run(restore, shell=True, env=env, check=True)
            filas = subprocess.run(
                ["psql", *base, "-t", "-c", "SELECT count(*) FROM analytics_metricwindow", BASE_TMP],
                env=env, capture_output=True, text=True, check=True).stdout.strip()
            JobRun.marcar("restore_check", ok=True, detalle=f"{filas} ventanas")
            self.stdout.write(self.style.SUCCESS(f"Restore OK: {filas} ventanas."))
        except subprocess.CalledProcessError as exc:
            JobRun.marcar("restore_check", ok=False, detalle=str(exc)[:200])
            raise
        finally:
            subprocess.run(["dropdb", "--if-exists", *base, BASE_TMP], env=env)
