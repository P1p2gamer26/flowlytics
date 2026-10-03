import pytest

from cameras.models import Camera
from tenancy.models import Business


@pytest.mark.django_db
def test_calibracion_tiene_defaults_neutros():
    biz = Business.objects.create(name="Tienda", kind="tienda")
    cam = Camera.objects.create(business=biz, name="Puerta", source="0")
    assert cam.altura_camara_m == 0
    assert cam.angulo_grados == 0
    assert cam.zona_muerta == []
    assert cam.lost_track_buffer == 30
