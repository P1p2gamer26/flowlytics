"""El contexto vive en la cámara y la zona puede sobrescribirlo."""
import pytest

from cameras.models import Camera, Zone
from tenancy.models import Business

pytestmark = pytest.mark.django_db

CUADRADO = [[0, 0], [10, 0], [10, 10], [0, 10]]


def _zona(contexto_camara, kind):
    biz = Business.objects.create(name="Mall", kind="tienda")
    cam = Camera.objects.create(business=biz, name="cam", source="0",
                                contexto=contexto_camara)
    return Zone.objects.create(camera=cam, name="z", kind=kind, polygon=CUADRADO)


def test_zona_sin_kind_hereda_el_contexto_de_la_camara():
    assert _zona("escaleras", "").contexto_efectivo == "escaleras"


def test_el_kind_de_la_zona_gana_sobre_el_de_la_camara():
    assert _zona("escaleras", "queue").contexto_efectivo == "queue"


def test_sin_contexto_en_ninguno_cae_en_general():
    assert _zona("", "").contexto_efectivo == "general"
