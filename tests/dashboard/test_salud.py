import pytest

from analytics.models import JobRun
from cameras.models import Camera, CameraHealth
from tenancy.models import Business


@pytest.mark.django_db
def test_salud_responde_json_sin_autenticacion(client):
    r = client.get("/salud/")
    assert r.status_code == 200
    data = r.json()
    assert "db" in data and "workers" in data and "jobs" in data


@pytest.mark.django_db
def test_salud_reporta_jobs_y_workers(client):
    biz = Business.objects.create(name="Cafe Secreto", kind="cafe")
    cam = Camera.objects.create(business=biz, name="Barra", source="0")
    CameraHealth.latir(cam, frames=10, reconexiones=0)
    JobRun.marcar("corpus")

    data = client.get("/salud/").json()

    assert data["jobs"]["corpus"]["ok"] is True
    assert len(data["workers"]) == 1


@pytest.mark.django_db
def test_salud_no_filtra_credenciales_ni_negocio(client):
    biz = Business.objects.create(name="Cafe Secreto", kind="cafe")
    cam = Camera.objects.create(business=biz, name="Barra",
                                source="rtsp://10.0.0.5:554/stream")
    cam.set_credencial("admin", "SuperSecreta123")
    cam.save()
    CameraHealth.latir(cam, frames=1, reconexiones=0)

    cuerpo = client.get("/salud/").content.decode()

    assert "SuperSecreta123" not in cuerpo
    assert "Cafe Secreto" not in cuerpo   # /salud/ es público: nada de negocio
