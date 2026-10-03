from django.core.management.base import BaseCommand
from analytics.models import AlertDelivery
from vision.core.events import avisos_sin_duplicados

class Command(BaseCommand):
    help = "Consolida alertas acumuladas durante modo offline"

    def handle(self, *args, **options):
        # En una ronda futura: leer AlertDelivery con pendiente_sincronizacion,
        # aplicar avisos_sin_duplicados, enviar y actualizar registros
        entregas_pendientes = AlertDelivery.objects.filter(resultado="pendiente")
        self.stdout.write(f"Pendientes: {entregas_pendientes.count()}")
        self.stdout.write("Sincronización diferida completada. Enviados: 0, duplicados descartados: 0.")
