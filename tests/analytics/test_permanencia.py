"""Permanencia media: cuánto se queda un cliente donde el negocio quiere que se quede.

No es la espera en fila (eso ya es `avg_queue_seconds`) ni el turno de un empleado.
"""
from datetime import date, datetime, timezone as dt_tz

import pytest

from analytics.aggregates import daily_summary
from analytics.models import MetricWindow

DIA = date(2026, 9, 1)


def _ventana(camera, zone_name, zone_kind, dwell):
    inicio = datetime(2026, 9, 1, 10, 0, tzinfo=dt_tz.utc)
    return MetricWindow.objects.create(
        camera=camera, zone_name=zone_name, zone_kind=zone_kind,
        started_at=inicio, ended_at=inicio, occupancy_avg=1.0, occupancy_max=1,
        dwell_seconds=dwell, unique_visitors=1)


@pytest.mark.django_db
def test_promedia_la_permanencia_de_las_zonas_de_cliente(camara_demo):
    _ventana(camara_demo, "Mesas", "general", 600.0)
    _ventana(camara_demo, "Terraza", "general", 300.0)

    assert daily_summary(camara_demo.business, DIA)["avg_dwell_seconds"] == 450.0


@pytest.mark.django_db
def test_la_fila_no_cuenta_como_permanencia(camara_demo):
    # Esperar 10 minutos de pie no es quedarse 10 minutos en la mesa: si la fila
    # entrara al promedio, un café con cola parecería un café donde la gente se
    # queda mucho.
    _ventana(camara_demo, "Mesas", "general", 600.0)
    _ventana(camara_demo, "Fila", "queue", 60.0)

    resumen = daily_summary(camara_demo.business, DIA)

    assert resumen["avg_dwell_seconds"] == 600.0
    assert resumen["avg_queue_seconds"] == 60.0


@pytest.mark.django_db
def test_el_turno_del_personal_no_cuenta_como_permanencia(camara_demo):
    # Un empleado está 8 horas en la barra. Meterlo al promedio lo dispara y deja
    # de describir al cliente.
    _ventana(camara_demo, "Mesas", "general", 600.0)
    _ventana(camara_demo, "Barra", "staff", 28800.0)

    assert daily_summary(camara_demo.business, DIA)["avg_dwell_seconds"] == 600.0


@pytest.mark.django_db
def test_sin_zonas_de_cliente_la_permanencia_es_none_y_no_cero(camara_demo):
    # "No hay dónde medirlo" no es "la gente no se queda". El panel pinta un
    # guion, igual que hace con la espera en fila.
    _ventana(camara_demo, "Fila", "queue", 60.0)

    assert daily_summary(camara_demo.business, DIA)["avg_dwell_seconds"] is None


@pytest.mark.django_db
def test_el_resumen_no_trae_el_rubro(camara_demo):
    # daily_summary lo consumen el corpus anónimo, los reportes y el humo. El
    # rubro lo añade la vista del panel, no el agregado.
    assert "rubro" not in daily_summary(camara_demo.business, DIA)
