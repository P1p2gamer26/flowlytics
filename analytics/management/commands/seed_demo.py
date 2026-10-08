"""Siembra un negocio de demostración con métricas sintéticas, para mostrar el
sistema sin cámaras ni videos. Idempotente: reusa el negocio/usuario/cámara y
reemplaza las métricas, así correrlo dos veces deja el mismo estado.

No corre YOLO ni abre video: inserta filas plausibles directo en la base. Para
demo con detecciones reales, usar run_camera sobre demo/videos/ (ver demo/README.md).
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from analytics.models import CrossingWindow, Event, MetricWindow
from analytics.avisos_demo import sembrar_avisos
from cameras.models import Camera, Zone
from tenancy.models import Business, Profile

ZONAS = [("Sala", "general"), ("Fila de caja", "queue"), ("Mostrador", "staff")]
# patrón horario: gente por hora del día (0..23), pico a media tarde
PERSONAS_POR_HORA = [0, 0, 0, 0, 0, 0, 1, 2, 4, 6, 8, 9,
                     10, 9, 11, 12, 10, 8, 6, 4, 3, 2, 1, 0]


class Command(BaseCommand):
    help = "Siembra un negocio de demostración con métricas sintéticas."

    def add_arguments(self, parser):
        parser.add_argument("--dias", type=int, default=14,
                            help="Cuántos días hacia atrás sembrar (default 14).")

    @transaction.atomic
    def handle(self, *args, **opts):
        biz, _ = Business.objects.get_or_create(
            name="Demo", defaults={"kind": "cafe"})
        user, creado = User.objects.get_or_create(username="demo")
        if creado:
            user.set_password("demo12345")
            user.save()
        Profile.objects.get_or_create(user=user, defaults={"role": "owner", "business": biz})
        cam, _ = Camera.objects.get_or_create(
            business=biz, name="Cámara demo", defaults={"source": "0"})
        for nombre, kind in ZONAS:
            Zone.objects.get_or_create(
                camera=cam, name=nombre,
                defaults={"kind": kind, "polygon": [[0, 0], [1, 0], [1, 1]]})

        # idempotencia: borra las métricas previas de la cámara demo y re-siembra
        MetricWindow.objects.filter(camera=cam).delete()
        CrossingWindow.objects.filter(camera=cam).delete()
        Event.objects.filter(camera=cam).delete()

        hoy = timezone.now().replace(minute=0, second=0, microsecond=0)
        for d in range(opts["dias"]):
            base = hoy - timedelta(days=d)
            for hora, personas in enumerate(PERSONAS_POR_HORA):
                if personas == 0:
                    continue
                inicio = base.replace(hour=hora)
                fin = inicio + timedelta(hours=1)
                for nombre, kind in ZONAS:
                    MetricWindow.objects.create(
                        camera=cam, zone_name=nombre, zone_kind=kind,
                        started_at=inicio, ended_at=fin,
                        occupancy_avg=personas * 0.6, occupancy_max=personas,
                        dwell_seconds=personas * 12.0 if kind == "queue" else 5.0,
                        unique_visitors=personas)
                CrossingWindow.objects.create(
                    camera=cam, line_name="Puerta", started_at=inicio, ended_at=fin,
                    entradas=personas, salidas=max(0, personas - 1))
                if personas >= 11:      # pico: dispara un evento de aforo
                    Event.objects.create(
                        camera=cam, kind="overcrowding", zone_name="Sala",
                        value=personas, occurred_at=inicio)

        sembrar_avisos(biz)
        self.stdout.write(self.style.SUCCESS(
            f"Demo sembrado: negocio '{biz.name}', usuario 'demo' / 'demo12345', "
            f"{opts['dias']} días de métricas."))
