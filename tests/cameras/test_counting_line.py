import pytest
from django.core.exceptions import ValidationError

from cameras.models import CountingLine, validate_line, Camera
from tenancy.models import Business


def test_validate_line_acepta_dos_puntos():
    validate_line([[10, 20], [30, 40]])   # no lanza


def test_validate_line_rechaza_una_linea_de_un_punto():
    with pytest.raises(ValidationError):
        validate_line([[10, 20]])


def test_validate_line_rechaza_coordenadas_no_enteras():
    with pytest.raises(ValidationError):
        validate_line([[10, 20], [30, "x"]])


@pytest.mark.django_db
def test_counting_line_se_guarda_ligada_a_la_camara():
    biz = Business.objects.create(name="Tienda", kind="tienda")
    cam = Camera.objects.create(business=biz, name="Puerta", source="0")
    linea = CountingLine.objects.create(camera=cam, name="entrada",
                                        puntos=[[0, 100], [200, 100]])
    assert cam.lines.count() == 1
    assert linea.invertir is False
