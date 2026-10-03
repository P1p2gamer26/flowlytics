from datetime import date, timedelta

from django.core.management.base import BaseCommand

from analytics.models import JobRun
from insights.client import LlmClient
from insights.services import generate_for_business
from tenancy.models import Business


class Command(BaseCommand):
    help = "Genera recomendaciones del LLM para el día indicado (por defecto, ayer)."

    def add_arguments(self, parser):
        parser.add_argument("--date", type=date.fromisoformat, default=None)
        parser.add_argument("--business", type=int, default=None)

    def handle(self, *args, **opts):
        day = opts["date"] or (date.today() - timedelta(days=1))
        businesses = Business.objects.all()
        if opts["business"]:
            businesses = businesses.filter(pk=opts["business"])

        llm = LlmClient()
        generados = 0
        for business in businesses:
            insight = generate_for_business(business, day, llm)
            if insight is None:
                self.stdout.write(f"{business.name}: sin datos para {day}, omitido.")
            else:
                generados += 1
                self.stdout.write(self.style.SUCCESS(f"{business.name}: insight generado."))
        JobRun.marcar("insights", detalle=f"{generados} insights para {day}")
