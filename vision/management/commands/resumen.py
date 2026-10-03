from django.core.management.base import BaseCommand
from vision.core.resumen import generar_resumen_diario
from vision.models import ResumenDia


class Command(BaseCommand):
    help = "Genera resumen diario conectable con métrica de negocio"

    def add_arguments(self, parser):
        parser.add_argument(
            "--rubro",
            type=str,
            default="",
            help="Clave del rubro de negocio",
        )

    def handle(self, *args, **options):
        rubro_clave = options.get("rubro", "")
        if not rubro_clave:
            self.stdout.write(self.style.ERROR("Falta --rubro"))
            return
        resultado = generar_resumen_diario(rubro_clave)
        if resultado is None:
            self.stdout.write(self.style.ERROR(f"Rubro desconocido: {rubro_clave}"))
            return
        ResumenDia.objects.create(
            metrica_principal=resultado.get("metrica_principal", ""),
            valor=resultado.get("valor", 0),
            negocio=rubro_clave,
        )
        self.stdout.write(self.style.SUCCESS(f"Resumen creado para {rubro_clave}"))
