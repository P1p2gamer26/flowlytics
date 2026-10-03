"""Borra métricas más viejas que la retención del plan de cada negocio.

Envoltura sobre queries de Django, como purge_clips/backup de la Fase 4: se corre
programado (systemd timer). La lógica de retención vive en Business.retencion_dias.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from analytics.models import CrossingWindow, Event, JobRun, MetricWindow
from tenancy.models import Business


class Command(BaseCommand):
    help = "Borra métricas más viejas que la retención del plan de cada negocio."

    def handle(self, *args, **opts):
        ahora = timezone.now()
        borradas = 0
        for biz in Business.objects.all():
            corte = ahora - timedelta(days=biz.retencion_dias)
            for modelo, campo in [(MetricWindow, "started_at"),
                                  (CrossingWindow, "started_at"),
                                  (Event, "occurred_at")]:
                n, _ = modelo.objects.filter(
                    camera__business=biz, **{f"{campo}__lt": corte}).delete()
                borradas += n
        JobRun.marcar("retencion", detalle=f"{borradas} filas")
        self.stdout.write(self.style.SUCCESS(f"Retención aplicada: {borradas} filas borradas."))
