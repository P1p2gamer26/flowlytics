from django.core.management.base import BaseCommand
from tenancy.rubros import RUBROS

class Command(BaseCommand):
    help = "Genera el reporte del primer día de instalación en local real"

    def handle(self, *args, **options):
        # Mínimo: confirma que hay rubros configurados y escribe un archivo
        if not RUBROS:
            self.stderr.write("No hay rubros configurados en tenancy/rubros.py")
            raise SystemExit(1)
        with open("reporte-primer-dia.md", "w") as f:
            f.write("# Reporte del primer día — Local real\n")
            f.write(f"Rubros disponibles: {list(RUBROS.keys())}\n")
            for clave, datos in RUBROS.items():
                f.write(f"- {clave}: métrica = {datos.get('metrica_principal', 'N/A')}\n")
        self.stdout.write("Reporte generado en reporte-primer-dia.md")
        raise SystemExit(0)
