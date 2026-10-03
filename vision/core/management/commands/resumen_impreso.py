import os
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Genera docs/resumen_impreso.md con la métrica del rubro del primer día"

    def handle(self, *args, **options):
        env = open(".env", encoding="utf-8").read()
        rubro = "desconocido"
        retencion = "30"
        for linea in env.splitlines():
            if linea.startswith("RUBRO="):
                rubro = linea.split("=", 1)[1]
            if linea.startswith("retencion_dias="):
                retencion = linea.split("=", 1)[1]
        metrica = f"fila_caja: 5 min (dato sintético/primer día, rubro: {rubro})\n"
        metrica += f"permanencia_mesa: 12 min (dato sintético/primer día, rubro: {rubro})\n"
        metrica += f"cola_mostrador: 3 min (dato sintético/primer día, rubro: {rubro})\n"
        metrica += f"rotacion: 80 clientes (dato sintético/primer día, rubro: {rubro})\n"
        metrica += f"retención aplicada: {retencion} días\n"
        with open("docs/resumen_impreso.md", "w", encoding="utf-8") as f:
            f.write(f"# Resumen impreso — Rubro: {rubro}\n")
            f.write(f"RUBRO: {rubro}\n")
            f.write(f"retencion_dias: {retencion}\n")
            f.write(metrica)
            f.write("Sin datos sensibles: sin track_id ni Recorrido.pistas.\n")
        self.stdout.write("PASS: docs/resumen_impreso.md generado")
