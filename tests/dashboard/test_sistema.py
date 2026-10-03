import pytest
from django.contrib.auth.models import User

from cameras.models import Camera, CameraHealth
from tenancy.models import Business, Profile


@pytest.fixture
def mundo(db):
    biz = Business.objects.create(name="Cafe", kind="cafe")
    cam = Camera.objects.create(business=biz, name="Barra", source="0")
    CameraHealth.latir(cam, frames=100, reconexiones=0)
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=biz)
    root = User.objects.create_user("root", password="x")
    Profile.objects.create(user=root, role="admin")
    return dict(ana=ana, root=root)


@pytest.mark.django_db
def test_dueno_no_entra_al_panel_de_sistema(client, mundo):
    client.force_login(mundo["ana"])
    r = client.get("/sistema/")
    assert r.status_code == 403


@pytest.mark.django_db
def test_admin_ve_el_panel(client, mundo):
    client.force_login(mundo["root"])
    r = client.get("/sistema/")
    assert r.status_code == 200
    assert "Barra" in r.content.decode()


@pytest.mark.django_db
def test_anonimo_es_redirigido(client, mundo):
    r = client.get("/sistema/")
    assert r.status_code == 302
