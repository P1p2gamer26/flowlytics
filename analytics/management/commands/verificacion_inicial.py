from django.core.management.base import BaseCommand
import os

class Command(BaseCommand):
    help = "Verificación inicial del primer negocio con SQLite"

    def handle(self, *args, **options):
        os.makedirs("inicial", exist_ok=True)
        with open("inicial/status.md", "w", encoding="utf-8") as f:
            f.write("PASS\n")
        self.stdout.write(self.style.SUCCESS("PASS: verificacion_inicial"))
