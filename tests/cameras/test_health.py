from datetime import timedelta

import pytest
from django.utils import timezone

from cameras.models import Camera, CameraHealth
from tenancy.models import Business


@pytest.fixture
def camara(db):
    biz = Business.objects.create(name="B", kind="cafe")
    return Camera.objects.create(business=biz, name="Barra", source="0")


@pytest.mark.django_db
def test_latir_crea_el_registro(camara):
    CameraHealth.latir(camara, frames=120, reconexiones=0)

    salud = CameraHealth.objects.get(camera=camara)
    assert salud.frames_leidos == 120
    assert salud.esta_viva() is True


@pytest.mark.django_db
def test_latir_actualiza_en_vez_de_duplicar(camara):
    CameraHealth.latir(camara, frames=10, reconexiones=0)
    CameraHealth.latir(camara, frames=20, reconexiones=1)

    assert CameraHealth.objects.count() == 1
    salud = CameraHealth.objects.get(camera=camara)
    assert salud.frames_leidos == 20
    assert salud.reconexiones == 1


@pytest.mark.django_db
def test_una_camara_sin_latido_reciente_esta_caida(camara):
    CameraHealth.latir(camara, frames=1, reconexiones=0)
    salud = CameraHealth.objects.get(camera=camara)
    salud.ultimo_latido = timezone.now() - timedelta(minutes=10)
    salud.save()

    assert salud.esta_viva(umbral_segundos=300) is False


@pytest.mark.django_db
def test_caidas_solo_devuelve_las_del_negocio(camara):
    otra_biz = Business.objects.create(name="Otro", kind="retail")
    ajena = Camera.objects.create(business=otra_biz, name="X", source="0")
    for cam in (camara, ajena):
        CameraHealth.latir(cam, frames=1, reconexiones=0)
        s = CameraHealth.objects.get(camera=cam)
        s.ultimo_latido = timezone.now() - timedelta(hours=1)
        s.save()

    caidas = CameraHealth.objects.caidas(camara.business)

    assert list(caidas) == [CameraHealth.objects.get(camera=camara)]


@pytest.mark.django_db
def test_registra_el_ultimo_error(camara):
    CameraHealth.latir(camara, frames=0, reconexiones=5,
                       error="no se pudo abrir la fuente")

    assert "no se pudo abrir" in CameraHealth.objects.get(camera=camara).ultimo_error
