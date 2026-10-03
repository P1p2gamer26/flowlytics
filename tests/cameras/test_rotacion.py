import pytest
from cryptography.fernet import Fernet, InvalidToken

from cameras.models import Camera, clave_desde_secreto
from cameras.rotacion import rotar
from tenancy.models import Business

VIEJO = "secreto-viejo-de-produccion"
NUEVO = "secreto-nuevo-rotado"


@pytest.fixture
def camara(db, settings):
    settings.SECRET_KEY = VIEJO
    biz = Business.objects.create(name="B", kind="cafe")
    cam = Camera.objects.create(business=biz, name="Puerta",
                                source="rtsp://10.0.0.5:554/stream")
    cam.set_credencial("admin", "SuperSecreta123")
    cam.save()
    return cam


@pytest.mark.django_db
def test_rotacion_conserva_la_credencial(camara, settings):
    rotar(Camera.objects.all(), clave_desde_secreto(VIEJO), clave_desde_secreto(NUEVO))

    settings.SECRET_KEY = NUEVO   # ahora el sistema usa la nueva
    url = Camera.objects.get(pk=camara.pk).url_conexion()
    assert url == "rtsp://admin:SuperSecreta123@10.0.0.5:554/stream"


@pytest.mark.django_db
def test_tras_rotar_la_clave_vieja_ya_no_descifra(camara):
    rotar(Camera.objects.all(), clave_desde_secreto(VIEJO), clave_desde_secreto(NUEVO))

    cifrada = bytes(Camera.objects.get(pk=camara.pk).credencial_cifrada)
    with pytest.raises(InvalidToken):
        Fernet(clave_desde_secreto(VIEJO)).decrypt(cifrada)


@pytest.mark.django_db
def test_camara_sin_credencial_no_estorba(camara, settings):
    biz = camara.business
    Camera.objects.create(business=biz, name="Webcam", source="0")   # sin credencial

    rotar(Camera.objects.all(), clave_desde_secreto(VIEJO), clave_desde_secreto(NUEVO))
    # no revienta y la que sí tenía credencial sigue recuperable
    settings.SECRET_KEY = NUEVO
    assert Camera.objects.get(pk=camara.pk)._password() == "SuperSecreta123"
