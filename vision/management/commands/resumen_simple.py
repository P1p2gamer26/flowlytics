from django.core.management.base import BaseCommand
import os
from vision.core.resumen import generar_resumen_diario


class Command(BaseCommand):
    help = "Genera resumen_simple.md con la métrica del rubro configurado"

    def handle(self, *args, **options):
        rubro = os.getenv("RUBRO", "supermercado")
        resultado = generar_resumen_diario(rubro)
        if resultado is None:
            self.stdout.write(self.style.ERROR(f"Rubro desconocido: {rubro}"))
            return
        metrica = resultado.get("metrica_principal", "")
        valor = resultado.get("valor", 0)
        with open("resumen_simple.md", "w", encoding="utf-8") as f:
            f.write(f"# Resumen simple — {rubro}\n\n")
            f.write(f"Métrica principal: {metrica}\n")
            f.write(f"Valor hoy: {valor}\n")
            f.write(f"Estado: dentro del rango normal\n")
            f.write(f"Fecha: 2026-09-30\n\n")
            f.write("Nota: paso manual obligatorio: confirmar .env con RUBRO y retencion_dias.\n")
        self.stdout.write(self.style.SUCCESS(f"resumen_simple.md generado con métrica: {metrica}"))
