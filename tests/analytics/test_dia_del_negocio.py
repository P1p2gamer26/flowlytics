"""El día de un negocio es el suyo, no el de UTC.

Bug medido el 6-sep-2026: en Bogotá (UTC-5) las métricas de las 19:49 locales se
guardan como 00:49 UTC del día siguiente. Con el día fijado en UTC, el panel
decía "hoy todavía no se ha registrado nadie" con la tienda llena de datos.
"""
from datetime import date, datetime, timezone as dt_tz

import pytest

from analytics.aggregates import _day_bounds, daily_summary
from analytics.models import MetricWindow


def test_el_dia_empieza_a_medianoche_en_la_zona_del_negocio():
    inicio, fin = _day_bounds(date(2026, 9, 6), "America/Bogota")
    # Medianoche en Bogotá son las 05:00 UTC del mismo día.
    assert inicio == datetime(2026, 9, 6, 5, 0, tzinfo=dt_tz.utc)
    # Y el día se cierra ya entrado el 7 en UTC: ahí está la tarde que se perdía.
    assert fin.astimezone(dt_tz.utc).day == 7


def test_sin_zona_se_comporta_como_antes():
    inicio, _ = _day_bounds(date(2026, 9, 6))
    assert inicio == datetime(2026, 9, 6, 0, 0, tzinfo=dt_tz.utc)


def test_una_zona_mal_escrita_no_deja_el_panel_en_blanco():
    inicio, _ = _day_bounds(date(2026, 9, 6), "No/Existe")
    assert inicio == datetime(2026, 9, 6, 0, 0, tzinfo=dt_tz.utc)


@pytest.mark.django_db
def test_la_tarde_cuenta_en_el_dia_de_la_tienda(camara_demo):
    """19:49 en Bogotá es el día 6, aunque en UTC ya sea el 7."""
    negocio = camara_demo.business
    negocio.timezone = "America/Bogota"
    negocio.save()
    cuando = datetime(2026, 9, 7, 0, 49, tzinfo=dt_tz.utc)   # 19:49 en Bogotá
    MetricWindow.objects.create(
        camera=camara_demo, zone_name="sugerida", zone_kind="general",
        started_at=cuando, ended_at=cuando, occupancy_avg=2.0, occupancy_max=7,
        dwell_seconds=3.0, unique_visitors=20)

    assert daily_summary(negocio, date(2026, 9, 6))["total_visitors"] == 20
    assert daily_summary(negocio, date(2026, 9, 7))["total_visitors"] in (None, 0)
