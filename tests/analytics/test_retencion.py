from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from analytics.models import MetricWindow
from cameras.models import Camera
from tenancy.models import Business, Plan


@pytest.mark.django_db
def test_borra_metricas_mas_viejas_que_la_retencion_del_plan():
    plan = Plan.objects.create(nombre="Corto", retencion_dias=30)
    biz = Business.objects.create(name="Neg", kind="cafe", plan=plan)
    cam = Camera.objects.create(business=biz, name="c", source="0")
    ahora = timezone.now()

    def ventana(dias_atras):
        t = ahora - timedelta(days=dias_atras)
        MetricWindow.objects.create(camera=cam, zone_name="z", zone_kind="general",
                                    started_at=t, ended_at=t, occupancy_avg=1.0,
                                    occupancy_max=1, dwell_seconds=0.0, unique_visitors=1)

    ventana(10)    # dentro de la retención: se queda
    ventana(60)    # fuera: se borra

    call_command("aplicar_retencion")

    restantes = list(MetricWindow.objects.filter(camera=cam))
    assert len(restantes) == 1
    assert (ahora - restantes[0].started_at).days < 30


@pytest.mark.django_db
def test_negocio_sin_plan_usa_la_retencion_por_defecto():
    biz = Business.objects.create(name="Sin plan", kind="cafe")   # 90 días por defecto
    cam = Camera.objects.create(business=biz, name="c", source="0")
    t = timezone.now() - timedelta(days=45)
    MetricWindow.objects.create(camera=cam, zone_name="z", zone_kind="general",
                                started_at=t, ended_at=t, occupancy_avg=1.0,
                                occupancy_max=1, dwell_seconds=0.0, unique_visitors=1)

    call_command("aplicar_retencion")

    assert MetricWindow.objects.filter(camera=cam).count() == 1   # 45 < 90: sobrevive
