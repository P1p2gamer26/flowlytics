from datetime import date

import pytest
from django.utils import timezone

from analytics.aggregates import daily_summary, hoy_del_negocio
from analytics.models import CrossingWindow
from cameras.models import Camera
from tenancy.models import Business


@pytest.fixture
def negocio(db):
    biz = Business.objects.create(name="Tienda", kind="tienda")
    cam = Camera.objects.create(business=biz, name="Puerta", source="0")
    return biz, cam


@pytest.mark.django_db
def test_suma_las_entradas_y_salidas_del_dia(negocio):
    biz, cam = negocio
    ahora = timezone.now()
    CrossingWindow.objects.create(camera=cam, line_name="puerta", started_at=ahora,
                                  ended_at=ahora, entradas=200, salidas=190)
    CrossingWindow.objects.create(camera=cam, line_name="puerta", started_at=ahora,
                                  ended_at=ahora, entradas=112, salidas=108)

    # El dia se pide en la zona de la tienda, no en UTC: a las 20:00 en Bogota
    # el servidor ya esta en el dia siguiente y `ahora.date()` pedia un dia en el
    # que la tienda ni habia abierto.
    s = daily_summary(biz, hoy_del_negocio(biz))

    assert s["entradas"] == 312
    assert s["salidas"] == 298


@pytest.mark.django_db
def test_sin_linea_dibujada_entradas_es_None_y_no_cero(negocio):
    """Cero es un dato ('no entró nadie'). None es la ausencia de dato ('nadie
    dibujó la línea'). El panel enseña cosas distintas."""
    biz, _ = negocio

    s = daily_summary(biz, date.today())

    assert s["entradas"] is None
    assert s["salidas"] is None


@pytest.mark.django_db
def test_no_cuenta_las_entradas_de_otro_dia(negocio):
    from datetime import timedelta

    biz, cam = negocio
    ayer = timezone.now() - timedelta(days=1)
    CrossingWindow.objects.create(camera=cam, line_name="puerta", started_at=ayer,
                                  ended_at=ayer, entradas=500, salidas=500)

    assert daily_summary(biz, timezone.now().date())["entradas"] is None