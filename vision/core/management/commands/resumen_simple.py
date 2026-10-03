from django.core.management.base import BaseCommand
from tenancy.rubros import RUBROS

class Command(BaseCommand):
    help = "Genera el resumen simple con la métrica del rubro"

    def handle(self, *args, **options):
        # En una ronda futura: leer ResumenDia y escribir el archivo
        rubro = "café"
        metrica = RUBROS[rubro]["metrica_principal"]
        self.stdout.write(self.style.SUCCESS(f"Métrica del rubro: {metrica}"))
