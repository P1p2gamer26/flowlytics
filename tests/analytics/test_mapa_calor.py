from datetime import date, datetime, timedelta, timezone as dt_tz

import pytest

from analytics.mapa_calor import mapa_calor_periodo
from analytics.models import HeatmapWindow


def _crear_ventana(camera, cuando, grid, personas):
    epoch = cuando.timestamp()
    HeatmapWindow.from_grid(camera, epoch, epoch + 60, grid, personas)


@pytest.mark.django_db
def test_sin_ventanas_en_el_rango_da_mensaje_honesto(camara_demo):
    r = mapa_calor_periodo(camara_demo, date(2026, 1, 1), date(2026, 1, 1))
    assert r["grid"] == []
    assert "Sin análisis" in r["mensaje"]


@pytest.mark.django_db
def test_menos_personas_que_el_umbral_no_pinta_el_mapa(camara_demo):
    camara_demo.business.timezone = "UTC"
    camara_demo.business.save()
    hoy = date.today()
    _crear_ventana(camara_demo, datetime.combine(hoy, datetime.min.time(), tzinfo=dt_tz.utc),
                   grid=[[1, 2]], personas=4)
    r = mapa_calor_periodo(camara_demo, hoy, hoy)
    assert r["grid"] == []
    assert "4 personas" in r["mensaje"]


@pytest.mark.django_db
def test_con_datos_suficientes_devuelve_la_rejilla_normalizada(camara_demo):
    from vision.core.heatmap import UMBRAL_PERSONAS

    camara_demo.business.timezone = "UTC"
    camara_demo.business.save()
    hoy = date.today()
    _crear_ventana(camara_demo, datetime.combine(hoy, datetime.min.time(), tzinfo=dt_tz.utc),
                   grid=[[0, 4]], personas=UMBRAL_PERSONAS)
    r = mapa_calor_periodo(camara_demo, hoy, hoy)
    assert r["mensaje"] == ""
    assert r["personas"] == UMBRAL_PERSONAS
    assert r["grid"], "con datos suficientes tiene que haber rejilla"


@pytest.mark.django_db
def test_la_franja_manana_no_incluye_ventanas_de_la_tarde(camara_demo):
    from vision.core.heatmap import UMBRAL_PERSONAS
    from zoneinfo import ZoneInfo

    hoy = date.today()
    tz = ZoneInfo(camara_demo.business.timezone or "UTC")
    manana = datetime.combine(hoy, datetime.min.time(), tzinfo=tz).replace(hour=8)
    tarde = manana.replace(hour=16)
    _crear_ventana(camara_demo, manana.astimezone(dt_tz.utc), grid=[[1]], personas=UMBRAL_PERSONAS)
    _crear_ventana(camara_demo, tarde.astimezone(dt_tz.utc), grid=[[9]], personas=UMBRAL_PERSONAS)

    r = mapa_calor_periodo(camara_demo, hoy, hoy, franja="manana")
    assert r["personas"] == UMBRAL_PERSONAS  # solo la ventana de la mañana
