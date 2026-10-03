"""La vista previa de una cámara en vivo, sin cámara: cv2 se sustituye por un doble."""
import numpy as np
import pytest
from django.contrib.auth.models import User

from cameras.models import Camera
from tenancy.models import Business, Profile

URL = "rtsp://10.0.0.5:554/stream1"


class CapturaFalsa:
    def __init__(self, da_frame=True, ancho=640, alto=480):
        self._da_frame, self._ancho, self._alto = da_frame, ancho, alto
        self.liberada = False

    def isOpened(self):
        return True

    def read(self):
        if not self._da_frame:
            return False, None
        return True, np.zeros((self._alto, self._ancho, 3), dtype=np.uint8)

    def get(self, prop):
        import cv2
        return {cv2.CAP_PROP_FRAME_WIDTH: self._ancho,
                cv2.CAP_PROP_FRAME_HEIGHT: self._alto}.get(prop, 0.0)

    def release(self):
        self.liberada = True


@pytest.fixture
def camara_rtsp(db):
    biz = Business.objects.create(name="A", kind="retail")
    dueno = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=dueno, role="owner", business=biz)
    cam = Camera.objects.create(business=biz, name="Puerta", source=URL)
    cam.set_credencial("admin", "SuperSecreta123")
    cam.save()
    cam.dueno = dueno
    return cam


@pytest.mark.django_db
def test_una_camara_en_vivo_da_su_frame_para_dibujar(api_client, camara_rtsp, monkeypatch):
    import cameras.api as api

    captura = CapturaFalsa()
    monkeypatch.setattr(api, "_abrir_stream", lambda url: captura)
    api_client.force_authenticate(camara_rtsp.dueno)

    r = api_client.get(f"/api/camaras/{camara_rtsp.pk}/vista/")

    assert r.status_code == 200
    assert r.json()["image"].startswith("data:image/jpeg;base64,")
    assert (r.json()["width"], r.json()["height"]) == (640, 480)
    assert r.json()["video"] is None
    assert captura.liberada is True


@pytest.mark.django_db
def test_la_vista_guarda_el_tamano_para_que_las_zonas_escalen(api_client, camara_rtsp,
                                                              monkeypatch):
    import cameras.api as api

    monkeypatch.setattr(api, "_abrir_stream", lambda url: CapturaFalsa())
    api_client.force_authenticate(camara_rtsp.dueno)

    api_client.get(f"/api/camaras/{camara_rtsp.pk}/vista/")

    camara_rtsp.refresh_from_db()
    assert (camara_rtsp.frame_w, camara_rtsp.frame_h) == (640, 480)


@pytest.mark.django_db
def test_la_vista_se_conecta_con_las_credenciales_guardadas(api_client, camara_rtsp,
                                                            monkeypatch):
    import cameras.api as api

    urls = []
    monkeypatch.setattr(api, "_abrir_stream",
                        lambda url: urls.append(url) or CapturaFalsa())
    api_client.force_authenticate(camara_rtsp.dueno)

    api_client.get(f"/api/camaras/{camara_rtsp.pk}/vista/")

    assert urls == ["rtsp://admin:SuperSecreta123@10.0.0.5:554/stream1"]


@pytest.mark.django_db
def test_si_no_hay_imagen_explica_por_que_y_no_filtra_la_contrasena(api_client, camara_rtsp,
                                                                    monkeypatch):
    import cameras.api as api

    monkeypatch.setattr(api, "_abrir_stream", lambda url: CapturaFalsa(da_frame=False))
    monkeypatch.setattr(api, "_sondear_tcp", lambda host, puerto: True)
    api_client.force_authenticate(camara_rtsp.dueno)

    r = api_client.get(f"/api/camaras/{camara_rtsp.pk}/vista/")

    assert r.status_code == 400
    assert "H.264" in r.json()["error"]
    assert "SuperSecreta123" not in r.content.decode()
