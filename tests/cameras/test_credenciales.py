import pytest

from cameras.models import Camera
from tenancy.models import Business


@pytest.fixture
def camara(db):
    biz = Business.objects.create(name="B", kind="retail")
    return Camera.objects.create(business=biz, name="Puerta",
                                 source="rtsp://10.0.0.5:554/stream")


@pytest.mark.django_db
def test_la_password_no_se_guarda_en_texto_plano(camara):
    camara.set_credencial("admin", "SuperSecreta123")
    camara.save()

    fila = Camera.objects.get(pk=camara.pk)
    assert "SuperSecreta123" not in str(fila.__dict__)
    assert b"SuperSecreta123" not in bytes(fila.credencial_cifrada)


@pytest.mark.django_db
def test_url_conexion_reconstruye_las_credenciales(camara):
    camara.set_credencial("admin", "SuperSecreta123")
    camara.save()

    url = Camera.objects.get(pk=camara.pk).url_conexion()

    assert url == "rtsp://admin:SuperSecreta123@10.0.0.5:554/stream"


@pytest.mark.django_db
def test_sin_credenciales_la_url_queda_igual(camara):
    assert camara.url_conexion() == "rtsp://10.0.0.5:554/stream"


@pytest.mark.django_db
def test_webcam_local_no_se_toca(db):
    biz = Business.objects.create(name="B", kind="cafe")
    cam = Camera.objects.create(business=biz, name="Webcam", source="0")

    assert cam.url_conexion() == 0


@pytest.mark.django_db
def test_el_str_del_modelo_no_filtra_credenciales(camara):
    camara.set_credencial("admin", "SuperSecreta123")

    assert "SuperSecreta123" not in str(camara)
    assert "admin" not in str(camara)
