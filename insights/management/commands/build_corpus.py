from datetime import date, timedelta

from django.core.management.base import BaseCommand

from analytics.models import JobRun
from insights.corpus import extraer_entrada
from tenancy.models import Business


class Command(BaseCommand):
    help = "Extrae las métricas anónimas del día al corpus comparativo."

    def add_arguments(self, parser):
        parser.add_argument("--date", type=date.fromisoformat, default=None)

    def handle(self, *args, **opts):
        day = opts["date"] or (date.today() - timedelta(days=1))
        creadas = 0
        for business in Business.objects.all():
            if extraer_entrada(business, day) is not None:
                creadas += 1
        JobRun.marcar("corpus", detalle=f"{creadas} entradas para {day}")
        self.stdout.write(self.style.SUCCESS(
            f"{creadas} entradas de corpus para {day}."))
