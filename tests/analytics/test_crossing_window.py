from types import SimpleNamespace

import pytest

from analytics.models import CrossingWindow
from cameras.models import Camera
from tenancy.models import Business


@pytest.mark.django_db
def test_from_summary_crea_una_fila_por_linea():
    biz = Business.objects.create(name="Tienda", kind="tienda")
    cam = Camera.objects.create(business=biz, name="Puerta", source="0")
    summary = SimpleNamespace(started_at=0.0, ended_at=60.0,
                              crossings={"entrada": (5, 2), "caja": (0, 3)})

    CrossingWindow.from_summary(cam, summary)

    filas = {c.line_name: (c.entradas, c.salidas) for c in cam.crossings.all()}
    assert filas == {"entrada": (5, 2), "caja": (0, 3)}


@pytest.mark.django_db
def test_from_summary_sin_lineas_no_crea_filas():
    biz = Business.objects.create(name="Tienda", kind="tienda")
    cam = Camera.objects.create(business=biz, name="Puerta", source="0")
    CrossingWindow.from_summary(cam, SimpleNamespace(started_at=0.0, ended_at=60.0, crossings={}))
    assert cam.crossings.count() == 0
