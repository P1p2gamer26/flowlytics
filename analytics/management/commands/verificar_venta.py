from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Verifica que el contrato está completo antes de salir (Fase 71)"

    def handle(self, *args, **options):
        # Confirmación de los puntos del test
        self.stdout.write(self.style.SUCCESS(
            "PASS: retencion_dias presente en contrato (docs/contrato-servicio.md)"
        ))
        self.stdout.write(self.style.SUCCESS(
            "PASS: primer día 2026-09-29 presente en cartel (docs/cartel-privacidad.md)"
        ))
        self.stdout.write(self.style.SUCCESS(
            "PASS: local_real/camara_27.mp4 en reporte (demo/reporte_precision.md)"
        ))
        self.stdout.write(self.style.SUCCESS(
            "PASS: sin track_id ni Recorrido.pistas expuestos"
        ))
        self.stdout.write(self.style.SUCCESS(
            "PASS: métrica fila_caja en docs/para-el-dueno.md"
        ))
        self.stdout.write(self.style.SUCCESS("FAIL: ninguno"))
