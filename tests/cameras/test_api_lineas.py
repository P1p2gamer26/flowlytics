import pytest
from django.contrib.auth.models import User

from cameras.models import Camera, CountingLine
from tenancy.models import Business, Plan, Profile

LINEA = [[10, 100], [200, 100]]


@pytest.fixture
def mundo(db):
    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    a = Business.objects.create(name="A", kind="cafe", plan=plan)
    b = Business.objects.create(name="B", kind="retail", plan=plan)
    cam_a = Camera.objects.create(business=a, name="ca", source="0")
    cam_b = Camera.objects.create(business=b, name="cb", source="0")
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    return dict(a=a, b=b, cam_a=cam_a, cam_b=cam_b, ana=ana)


@pytest.mark.django_db
def test_crear_linea_con_dos_puntos(api_client, mundo):
    api_client.force_authenticate(mundo["ana"])

    r = api_client.post(f"/api/camaras/{mundo['cam_a'].pk}/lineas/",
                        {"name": "puerta", "puntos": LINEA}, format="json")

    assert r.status_code == 201
    assert r.json()["invertir"] is False
    assert CountingLine.objects.filter(camera=mundo["cam_a"], name="puerta").exists()


@pytest.mark.django_db
def test_rechaza_una_linea_que_no_son_dos_puntos(api_client, mundo):
    api_client.force_authenticate(mundo["ana"])

    r = api_client.post(f"/api/camaras/{mundo['cam_a'].pk}/lineas/",
                        {"name": "mala", "puntos": [[10, 100]]}, format="json")

    assert r.status_code == 400
    assert not CountingLine.objects.filter(name="mala").exists()


@pytest.mark.django_db
def test_listar_lineas_de_la_camara(api_client, mundo):
    CountingLine.objects.create(camera=mundo["cam_a"], name="puerta", puntos=LINEA)
    api_client.force_authenticate(mundo["ana"])

    r = api_client.get(f"/api/camaras/{mundo['cam_a'].pk}/lineas/")

    assert r.status_code == 200
    assert [ln["name"] for ln in r.json()] == ["puerta"]


@pytest.mark.django_db
def test_invertir_el_sentido_sin_volver_a_dibujar(api_client, mundo):
    """El sentido casi nunca se acierta a la primera: cambiarlo no puede obligar
    a borrar la línea y dibujarla al revés."""
    linea = CountingLine.objects.create(camera=mundo["cam_a"], name="puerta", puntos=LINEA)
    api_client.force_authenticate(mundo["ana"])

    r = api_client.put(f"/api/lineas/{linea.pk}/", {"invertir": True}, format="json")

    assert r.status_code == 200
    linea.refresh_from_db()
    assert linea.invertir is True


@pytest.mark.django_db
def test_borrar_linea(api_client, mundo):
    linea = CountingLine.objects.create(camera=mundo["cam_a"], name="puerta", puntos=LINEA)
    api_client.force_authenticate(mundo["ana"])

    r = api_client.delete(f"/api/lineas/{linea.pk}/")

    assert r.status_code in (200, 204)
    assert not CountingLine.objects.filter(pk=linea.pk).exists()


@pytest.mark.django_db
def test_la_camara_serializa_sus_lineas(api_client, mundo):
    """El editor pinta las líneas guardadas con la misma respuesta que ya pide
    para las zonas: una ronda de red, no dos."""
    CountingLine.objects.create(camera=mundo["cam_a"], name="puerta", puntos=LINEA)
    api_client.force_authenticate(mundo["ana"])

    r = api_client.get(f"/api/camaras/{mundo['cam_a'].pk}/")

    assert [ln["name"] for ln in r.json()["lines"]] == ["puerta"]
