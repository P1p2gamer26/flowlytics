"""Cada cámara tiene su propia página (el shell de React; la ruta existe
y exige sesión). Los datos de la cámara y sus zonas los sirve la API,
probada en tests/cameras/test_api.py."""
import pytest
from django.contrib.auth.models import User

from cameras.models import Camera
from tenancy.models import Business, Profile


@pytest.fixture
def mundo(db):
    biz = Business.objects.create(name="A", kind="cafe")
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=biz)
    return dict(biz=biz, ana=ana)


@pytest.mark.django_db
def test_la_pagina_de_la_camara_existe(client, mundo):
    cam = Camera.objects.create(business=mundo["biz"], name="Puerta",
                                source="0", contexto="entrada")
    client.force_login(mundo["ana"])

    r = client.get(f"/camaras/{cam.pk}/")

    assert r.status_code == 200


@pytest.mark.django_db
def test_sin_login_redirige(client, mundo):
    cam = Camera.objects.create(business=mundo["biz"], name="P", source="0")

    r = client.get(f"/camaras/{cam.pk}/")

    assert r.status_code == 302


@pytest.mark.django_db
def test_la_pantalla_de_camara_trae_zonas_y_lineas_en_una_sola_peticion(client_demo,
                                                                        camara_demo):
    """El editor dibuja las dos cosas sobre el mismo lienzo: si vinieran en dos
    respuestas distintas, se pintarían desincronizadas."""
    from cameras.models import CountingLine

    CountingLine.objects.create(camera=camara_demo, name="puerta",
                                puntos=[[0, 100], [200, 100]])

    datos = client_demo.get(f"/api/camaras/{camara_demo.pk}/").json()

    assert [z["name"] for z in datos["zones"]] == ["zona"]
    assert [ln["name"] for ln in datos["lines"]] == ["puerta"]

