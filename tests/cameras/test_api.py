import pytest
from django.contrib.auth.models import User

from cameras.models import Camera, Zone
from tenancy.models import Business, Plan, Profile

POLIGONO = [[0, 0], [10, 0], [10, 10], [0, 10]]


@pytest.fixture
def mundo(db):
    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    a = Business.objects.create(name="A", kind="cafe", plan=plan)
    b = Business.objects.create(name="B", kind="retail", plan=plan)
    cam_a = Camera.objects.create(business=a, name="ca", source="0")
    cam_b = Camera.objects.create(business=b, name="cb", source="0")
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    root = User.objects.create_user("root", password="x")
    Profile.objects.create(user=root, role="admin")
    return dict(a=a, b=b, cam_a=cam_a, cam_b=cam_b, ana=ana, root=root)


@pytest.mark.django_db
def test_dueno_lista_solo_sus_camaras(api_client, mundo):
    api_client.force_authenticate(mundo["ana"])

    r = api_client.get("/api/camaras/", {"business": mundo["a"].pk})

    assert r.status_code == 200
    assert [c["name"] for c in r.json()] == ["ca"]


@pytest.mark.django_db
def test_dueno_no_ve_camaras_de_otro_negocio(api_client, mundo):
    api_client.force_authenticate(mundo["ana"])

    r = api_client.get("/api/camaras/", {"business": mundo["b"].pk})

    assert r.status_code == 403


@pytest.mark.django_db
def test_dueno_crea_camara_en_su_negocio(api_client, mundo):
    api_client.force_authenticate(mundo["ana"])

    r = api_client.post("/api/camaras/", {"business": mundo["a"].pk,
                                          "name": "nueva", "source": "0"})

    assert r.status_code == 201
    assert Camera.objects.filter(business=mundo["a"], name="nueva").exists()


@pytest.mark.django_db
def test_dueno_no_puede_crear_camara_en_negocio_ajeno(api_client, mundo):
    api_client.force_authenticate(mundo["ana"])

    r = api_client.post("/api/camaras/", {"business": mundo["b"].pk,
                                          "name": "intrusa", "source": "0"})

    assert r.status_code == 403
    assert not Camera.objects.filter(name="intrusa").exists()


@pytest.mark.django_db
def test_dueno_no_puede_borrar_camara_ajena(api_client, mundo):
    api_client.force_authenticate(mundo["ana"])

    r = api_client.delete(f"/api/camaras/{mundo['cam_b'].pk}/")

    assert r.status_code in (403, 404)
    assert Camera.objects.filter(pk=mundo["cam_b"].pk).exists()


@pytest.mark.django_db
def test_crear_zona_con_poligono_valido(api_client, mundo):
    api_client.force_authenticate(mundo["ana"])

    r = api_client.post(f"/api/camaras/{mundo['cam_a'].pk}/zonas/",
                        {"name": "fila", "kind": "queue", "polygon": POLIGONO},
                        format="json")

    assert r.status_code == 201
    assert Zone.objects.filter(camera=mundo["cam_a"], name="fila").exists()


@pytest.mark.django_db
def test_rechaza_poligono_invalido(api_client, mundo):
    api_client.force_authenticate(mundo["ana"])

    r = api_client.post(f"/api/camaras/{mundo['cam_a'].pk}/zonas/",
                        {"name": "mala", "kind": "queue", "polygon": [[0, 0], [1, 1]]},
                        format="json")

    assert r.status_code == 400
    assert not Zone.objects.filter(name="mala").exists()


@pytest.mark.django_db
def test_borrar_zona_la_quita_de_la_camara(api_client, mundo):
    zona = Zone.objects.create(camera=mundo["cam_a"], name="fila", kind="queue",
                               polygon=POLIGONO)
    api_client.force_authenticate(mundo["ana"])

    r = api_client.delete(f"/api/zonas/{zona.pk}/")

    assert r.status_code in (200, 204)
    assert not Zone.objects.filter(pk=zona.pk).exists()


@pytest.mark.django_db
def test_no_se_puede_borrar_la_zona_de_otro_negocio(api_client, mundo):
    zona = Zone.objects.create(camera=mundo["cam_b"], name="ajena", kind="general",
                               polygon=POLIGONO)
    api_client.force_authenticate(mundo["ana"])

    r = api_client.delete(f"/api/zonas/{zona.pk}/")

    assert r.status_code in (403, 404)
    assert Zone.objects.filter(pk=zona.pk).exists()


@pytest.mark.django_db
def test_admin_puede_operar_sobre_cualquier_negocio(api_client, mundo):
    api_client.force_authenticate(mundo["root"])

    r = api_client.get("/api/camaras/", {"business": mundo["b"].pk})

    assert r.status_code == 200
    assert [c["name"] for c in r.json()] == ["cb"]
