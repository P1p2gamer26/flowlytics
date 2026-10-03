import pytest
from django.utils import timezone

from vision.humo import datos_del_informe, informe, resumen_de_camara

VIDEO = {"ancho": 640, "alto": 360, "fps": 25.0, "frames": 2700,
         "duracion_s": 108.0, "h264": True}


@pytest.mark.django_db
def test_el_informe_dice_cuanta_gente_conto_y_en_que_zonas(camara_demo, ventana_demo):
    datos = datos_del_informe(camara_demo, timezone.now().date(), VIDEO,
                              muestras_sugerencia=57)

    texto = informe(datos)

    assert "640×360" in texto
    assert "Ventanas cerradas: **1**" in texto
    assert "57 detecciones" in texto
    assert "zona" in texto              # la zona de camara_demo
    assert "Visitantes únicos del día: **1**" in texto


@pytest.mark.django_db
def test_sin_ventanas_el_informe_lo_dice_en_vez_de_salir_vacio(camara_demo):
    datos = datos_del_informe(camara_demo, timezone.now().date(), VIDEO)

    texto = informe(datos)

    assert "No se cerró ninguna ventana" in texto


@pytest.mark.django_db
def test_los_avisos_salen_en_el_informe(camara_demo):
    datos = datos_del_informe(camara_demo, timezone.now().date(), VIDEO,
                              avisos=["el video no es H.264"])

    assert "el video no es H.264" in informe(datos)


@pytest.mark.django_db
def test_los_eventos_y_los_cruces_aparecen(camara_demo):
    from analytics.models import CrossingWindow, Event

    ahora = timezone.now()
    Event.objects.create(camera=camara_demo, kind="long_queue", zone_name="zona",
                         value=200.0, occurred_at=ahora)
    CrossingWindow.objects.create(camera=camara_demo, line_name="puerta",
                                  started_at=ahora, ended_at=ahora,
                                  entradas=12, salidas=9)

    texto = informe(datos_del_informe(camara_demo, ahora.date(), VIDEO))

    assert "long_queue" in texto
    assert "puerta" in texto
    assert "12" in texto and "9" in texto


@pytest.mark.django_db
def test_el_resumen_es_de_la_camara_y_no_del_negocio(camara_demo):
    """Dos corridas de humo en el mismo negocio no pueden sumarse entre si.

    Reproduce el bug del 6-sep: el informe daba 120 visitantes cuando la corrida
    habia contado 78, porque el otro 42 era de la corrida anterior.
    """
    from analytics.models import MetricWindow
    from cameras.models import Camera

    otra = Camera.objects.create(business=camara_demo.business, name="corrida vieja",
                                 source=camara_demo.source)
    ahora = timezone.now()
    MetricWindow.objects.create(camera=otra, zone_name="sugerida", zone_kind="general",
                                started_at=ahora, ended_at=ahora,
                                occupancy_avg=1.0, occupancy_max=3,
                                dwell_seconds=2.0, unique_visitors=42)
    MetricWindow.objects.create(camera=camara_demo, zone_name="sugerida",
                                zone_kind="general", started_at=ahora, ended_at=ahora,
                                occupancy_avg=2.0, occupancy_max=9,
                                dwell_seconds=4.0, unique_visitors=26)

    r = resumen_de_camara(camara_demo)
    assert r["total_visitors"] == 26, "se colo el conteo de otra camara del mismo negocio"
    assert r["peak_occupancy"] == 9


@pytest.mark.django_db
def test_sin_ventanas_no_inventa_numeros(camara_demo):
    r = resumen_de_camara(camara_demo)
    assert r["total_visitors"] == 0
    assert r["peak_occupancy"] == 0
    assert r["peak_hour"] is None
    assert r["dwell_promedio"] is None

