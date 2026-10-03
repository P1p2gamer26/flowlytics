import cv2
import numpy as np
import pytest
from django.contrib.auth.models import User

from cameras.models import Camera
from tenancy.models import Business, Profile


def generar_video(ruta, fps=2.0, frames=4, ancho=32, alto=24):
    writer = cv2.VideoWriter(str(ruta), cv2.VideoWriter_fourcc(*"mp4v"), fps, (ancho, alto))
    for i in range(frames):
        writer.write(np.full((alto, ancho, 3), i * 40, dtype=np.uint8))
    writer.release()


@pytest.fixture
def mundo(db):
    biz = Business.objects.create(name="A", kind="cafe")
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=biz)
    return dict(biz=biz, ana=ana)


@pytest.mark.django_db
def test_vista_de_archivo_devuelve_frame_y_guarda_dimensiones(api_client, mundo, tmp_path):
    video = tmp_path / "tienda.mp4"
    generar_video(video)
    cam = Camera.objects.create(business=mundo["biz"], name="Tienda",
                                source=f"file://{video}")
    api_client.force_authenticate(mundo["ana"])

    r = api_client.get(f"/api/camaras/{cam.pk}/vista/")

    assert r.status_code == 200
    data = r.json()
    assert data["width"] == 32
    assert data["height"] == 24
    assert data["image"].startswith("data:image/jpeg;base64,")
    cam.refresh_from_db()
    assert (cam.frame_w, cam.frame_h) == (32, 24)


@pytest.mark.django_db
def test_vista_rechaza_rtsp(api_client, mundo):
    cam = Camera.objects.create(business=mundo["biz"], name="RTSP",
                                source="rtsp://10.0.0.5:554/stream")
    api_client.force_authenticate(mundo["ana"])

    r = api_client.get(f"/api/camaras/{cam.pk}/vista/")

    assert r.status_code == 400


@pytest.mark.django_db
def test_vista_de_camara_ajena_es_403(api_client, mundo, tmp_path):
    otra = Business.objects.create(name="B", kind="retail")
    cam = Camera.objects.create(business=otra, name="Ajena", source="0")
    api_client.force_authenticate(mundo["ana"])

    r = api_client.get(f"/api/camaras/{cam.pk}/vista/")

    assert r.status_code in (403, 404)
