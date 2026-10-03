"""El editor puede pedir los recorridos de una cámara para visualizarlos."""
import pytest

from analytics.models import Trajectory


@pytest.mark.django_db
def test_el_endpoint_sirve_los_recorridos_de_la_camara(client_demo, camara_demo):
    t = Trajectory.objects.create(
        camera=camara_demo,
        started_at="2026-09-06T10:00:00Z",
        ended_at="2026-09-06T10:01:00Z",
        track_id=5,
        points=[[100, 200], [120, 210], [140, 220]],
        duration=60.0,
    )
    r = client_demo.get(f"/api/camaras/{camara_demo.pk}/trayectorias/")

    assert r.status_code == 200
    assert len(r.data["recorridos"]) == 1
    assert r.data["recorridos"][0]["track_id"] == 5
    assert r.data["recorridos"][0]["points"] == [[100, 200], [120, 210], [140, 220]]


@pytest.mark.django_db
def test_solo_devuelve_la_camara_solicitada(client_demo, camara_demo, db):
    from cameras.models import Camera, Business
    otra = Camera.objects.create(business=Business.objects.create(name="Otra"), name="otra")
    Trajectory.objects.create(
        camera=otra, started_at="2026-09-06T10:00:00Z", ended_at="2026-09-06T10:01:00Z",
        track_id=1, points=[[1, 2], [3, 4]], duration=1.0)

    r = client_demo.get(f"/api/camaras/{camara_demo.pk}/trayectorias/")

    assert r.status_code == 200
    assert len(r.data["recorridos"]) == 0


@pytest.mark.django_db
def test_una_camara_ajena_devuelve_403(client_sin_negocio, camara_demo):
    r = client_sin_negocio.get(f"/api/camaras/{camara_demo.pk}/trayectorias/")

    assert r.status_code in (403, 404)


@pytest.mark.django_db
def test_sin_recorridos_devuelve_lista_vacia(client_demo, camara_demo):
    r = client_demo.get(f"/api/camaras/{camara_demo.pk}/trayectorias/")

    assert r.status_code == 200
    assert r.data["recorridos"] == []
