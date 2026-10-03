from django.core.management.base import BaseCommand
from django.utils import timezone
from analytics.models import JobRun

class Command(BaseCommand):
    help = "Ejecuta respaldo automático y registra en JobRun"

    def handle(self, *args, **options):
        try:
            from django.core.management import call_command
            call_command("exportar_respaldo", stdout=options.get("stdout"))
            detalle = "respaldo_creado"
            ok = True
        except Exception as exc:
            detalle = str(exc)
            ok = False
        JobRun.marcar("respaldo_automatico", ok=ok, detalle=detalle)
        self.stdout.write(f"Respaldo programado: ok={ok} detalle={detalle}")
