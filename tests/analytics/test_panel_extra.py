import pytest


@pytest.mark.django_db
def test_devuelve_las_tres_piezas(client_demo, camara_demo):
    r = client_demo.get(f"/api/panel-extra/?business={camara_demo.business.pk}")
    assert r.status_code == 200
    assert set(r.data) == {"camaras_caidas", "comparativa", "recomendacion"}
    # Sin corpus ni insights todavía: honesto, no inventado.
    assert r.data["comparativa"] is None
    assert r.data["recomendacion"] == ""


@pytest.mark.django_db
def test_lista_las_camaras_sin_senal(client_demo, camara_demo):
    from datetime import timedelta

    from django.utils import timezone

    from cameras.models import CameraHealth

    CameraHealth.objects.update_or_create(
        camera=camara_demo,
        defaults={"ultimo_latido": timezone.now() - timedelta(hours=3),
                  "ultimo_error": "RTSP timeout"},
    )
    r = client_demo.get(f"/api/panel-extra/?business={camara_demo.business.pk}")
    caidas = r.data["camaras_caidas"]
    assert len(caidas) == 1
    assert caidas[0]["camara"] == camara_demo.name
    assert caidas[0]["ultimo_error"] == "RTSP timeout"


@pytest.mark.django_db
def test_devuelve_la_recomendacion_del_dia(client_demo, camara_demo):
    from insights.models import Insight

    from analytics.aggregates import hoy_del_negocio

    Insight.objects.create(business=camara_demo.business,
                           day=hoy_del_negocio(camara_demo.business),
                           body="Refuerza caja entre 6 y 8 pm.", model="test")
    r = client_demo.get(f"/api/panel-extra/?business={camara_demo.business.pk}")
    assert r.data["recomendacion"] == "Refuerza caja entre 6 y 8 pm."


@pytest.mark.django_db
def test_no_deja_ver_otro_negocio(client_demo):
    from tenancy.models import Business

    ajeno = Business.objects.create(name="Ajeno", kind="cafe")
    assert client_demo.get(f"/api/panel-extra/?business={ajeno.pk}").status_code == 403
