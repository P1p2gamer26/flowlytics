import os
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Genera reporte del piloto (SQLite, sin Postgres)"

    def handle(self, *args, **options):
        # Leer datos del piloto (SQLite local)
        # Reusar modelos existentes: analytics.models.Event, MarcaPersona
        from analytics.models import Event
        total = Event.objects.filter(kind__in=["long_queue", "full_local"]).count()
        # Escribir archivo de texto con los números
        os.makedirs("piloto", exist_ok=True)
        with open("piloto/reporte.md", "w") as f:
            f.write("# Reporte del piloto (4h)\n\n")
            f.write(f"- Métrica del rubro: consultar `tenancy/rubros.py`.\n")
            f.write(f"- Eventos detectados: {total}\n")
            f.write(f"- Datos almacenados: SQLite (`db.sqlite3`).\n")
            f.write(f"- Privacidad: ver `docs/cartel-privacidad.md`.\n")
        self.stdout.write("Reporte generado en piloto/reporte.md")
        return 0
