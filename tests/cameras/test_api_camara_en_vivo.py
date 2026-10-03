import pytest
from django.contrib.auth.models import User

from cameras.models import Camera
from tenancy.models import Business, Plan, Profile

URL = "rtsp://10.0.0.5:554/stream1"


@pytest.fixture
def mundo(db):
    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    a = Business.objects.create(name="A", kind="retail", plan=plan)
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    return dict(a=a, ana=ana)


@pytest.mark.django_db
def test_crear_una_camara_rtsp_con_credenciales(api_client, mundo):
    api_client.force_authenticate(mundo["ana"])

    r = api_client.post("/api/camaras/",
                        {"business": mundo["a"].pk, "name": "Puerta", "source": URL,
                         "usuario": "admin", "password": "SuperSecreta123"},
                        format="json")

    assert r.status_code == 201
    cam = Camera.objects.get(name="Puerta")
    assert cam.url_conexion() == "rtsp://admin:SuperSecreta123@10.0.0.5:554/stream1"


@pytest.mark.django_db
def test_la_contrasena_no_vuelve_en_la_respuesta(api_client, mundo):
    api_client.force_authenticate(mundo["ana"])

    r = api_client.post("/api/camaras/",
                        {"business": mundo["a"].pk, "name": "Puerta", "source": URL,
                         "usuario": "admin", "password": "SuperSecreta123"},
                        format="json")

    cuerpo = r.content.decode()
    assert "SuperSecreta123" not in cuerpo
    assert "password" not in r.json()
    assert r.json()["usuario"] == "admin"


@pytest.mark.django_db
def test_al_leer_la_camara_tampoco_sale_la_contrasena(api_client, mundo):
    cam = Camera.objects.create(business=mundo["a"], name="Puerta", source=URL)
    cam.set_credencial("admin", "SuperSecreta123")
    cam.save()
    api_client.force_authenticate(mundo["ana"])

    r = api_client.get(f"/api/camaras/{cam.pk}/")

    assert "SuperSecreta123" not in r.content.decode()


@pytest.mark.django_db
def test_cambiar_la_contrasena_sin_reescribir_la_direccion(api_client, mundo):
    cam = Camera.objects.create(business=mundo["a"], name="Puerta", source=URL)
    cam.set_credencial("admin", "Vieja123")
    cam.save()
    api_client.force_authenticate(mundo["ana"])

    r = api_client.put(f"/api/camaras/{cam.pk}/",
                       {"usuario": "admin", "password": "Nueva456"}, format="json")

    assert r.status_code == 200
    assert Camera.objects.get(pk=cam.pk).url_conexion().endswith("Nueva456@10.0.0.5:554/stream1")


@pytest.mark.django_db
def test_guardar_sin_tocar_la_contrasena_no_la_borra(api_client, mundo):
    cam = Camera.objects.create(business=mundo["a"], name="Puerta", source=URL)
    cam.set_credencial("admin", "SuperSecreta123")
    cam.save()
    api_client.force_authenticate(mundo["ana"])

    api_client.put(f"/api/camaras/{cam.pk}/", {"name": "Puerta principal"}, format="json")

    cam = Camera.objects.get(pk=cam.pk)
    assert cam.name == "Puerta principal"
    assert cam.url_conexion() == "rtsp://admin:SuperSecreta123@10.0.0.5:554/stream1"
