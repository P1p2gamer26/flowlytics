from datetime import date, datetime, timezone as dt_tz

import pytest

from analytics.models import CrossingWindow, MetricWindow
from analytics.reportes import reporte_periodo
from cameras.models import Camera
from tenancy.models import Business


def _dt(y, m, d, h=12):
    return datetime(y, m, d, h, tzinfo=dt_tz.utc)


@pytest.fixture
def negocio_con_datos(db):
    biz = Business.objects.create(name="Neg", kind="cafe")
    cam = Camera.objects.create(business=biz, name="c", source="0")
    # día 10: 2 ventanas de aforo + cruces
    MetricWindow.objects.create(camera=cam, zone_name="sala", zone_kind="general",
                                started_at=_dt(2026, 8, 10), ended_at=_dt(2026, 8, 10),
                                occupancy_avg=3.0, occupancy_max=5,
                                dwell_seconds=0.0, unique_visitors=8)
    CrossingWindow.objects.create(camera=cam, line_name="puerta",
                                  started_at=_dt(2026, 8, 10), ended_at=_dt(2026, 8, 10),
                                  entradas=8, salidas=6)
    # día 11: sin datos
    return biz, cam


@pytest.mark.django_db
def test_reporte_una_fila_por_dia_del_rango(negocio_con_datos):
    biz, _ = negocio_con_datos
    filas = reporte_periodo(biz, date(2026, 8, 10), date(2026, 8, 12))
    assert [f["fecha"] for f in filas] == ["2026-08-10", "2026-08-11", "2026-08-12"]


@pytest.mark.django_db
def test_reporte_suma_visitantes_aforo_y_cruces(negocio_con_datos):
    biz, _ = negocio_con_datos
    fila = reporte_periodo(biz, date(2026, 8, 10), date(2026, 8, 10))[0]
    assert fila["visitantes"] == 8
    assert fila["aforo_pico"] == 5
    assert fila["entradas"] == 8
    assert fila["salidas"] == 6


@pytest.mark.django_db
def test_dia_sin_datos_sale_en_ceros(negocio_con_datos):
    biz, _ = negocio_con_datos
    fila = reporte_periodo(biz, date(2026, 8, 11), date(2026, 8, 11))[0]
    assert fila["visitantes"] == 0
    assert fila["entradas"] == 0
    assert fila["salidas"] == 0
