from datetime import date, timedelta

import pytest


@pytest.mark.django_db
def test_sin_datos_devuelve_mensaje_y_200(client_demo, camara_demo):
    r = client_demo.get(f"/api/camaras/{camara_demo.pk}/mapa_calor/")
    assert r.status_code == 200
    assert r.data["grid"] == []
    assert r.data["mensaje"]


@pytest.mark.django_db
def test_con_datos_suficientes_devuelve_la_rejilla(client_demo, camara_demo):
    from analytics.models import HeatmapWindow
    from django.utils import timezone
    from vision.core.heatmap import UMBRAL_PERSONAS

    ahora = timezone.now()
    HeatmapWindow.from_grid(camara_demo, ahora.timestamp(), ahora.timestamp() + 60,
                            grid=[[1, 2], [3, 4]], personas=UMBRAL_PERSONAS)
    r = client_demo.get(f"/api/camaras/{camara_demo.pk}/mapa_calor/")
    assert r.data["mensaje"] == ""
    assert r.data["cols"] == 2 and r.data["rows"] == 2


@pytest.mark.django_db
def test_una_fecha_invalida_da_400(client_demo, camara_demo):
    r = client_demo.get(f"/api/camaras/{camara_demo.pk}/mapa_calor/?desde=no-es-fecha")
    assert r.status_code == 400


@pytest.mark.django_db
def test_no_se_puede_pedir_el_mapa_de_la_camara_de_otro(client_demo, db):
    from cameras.models import Camera
    from tenancy.models import Business

    ajena = Camera.objects.create(business=Business.objects.create(name="Otra", kind="cafe"),
                                  name="Ajena", source="0")
    r = client_demo.get(f"/api/camaras/{ajena.pk}/mapa_calor/")
    assert r.status_code == 403
