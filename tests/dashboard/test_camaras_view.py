import pytest
from django.contrib.auth.models import User

from cameras.models import Camera
from tenancy.models import Business, Profile


@pytest.fixture
def dueno(db):
    biz = Business.objects.create(name="Cafe Uno", kind="cafe")
    Camera.objects.create(business=biz, name="Barra", source="0")
    user = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=user, role="owner", business=biz)
    return user, biz


@pytest.mark.django_db
def test_anonimo_es_redirigido(client, dueno):
    r = client.get("/camaras/")

    assert r.status_code == 302


@pytest.mark.django_db
def test_dueno_ve_sus_camaras(client, dueno):
    user, biz = dueno
    client.force_login(user)

    r = client.get(f"/api/camaras/?business={biz.pk}")

    assert r.status_code == 200
    assert any(c["name"] == "Barra" for c in r.data)


@pytest.mark.django_db
def test_no_ve_camaras_de_otro_negocio(client, dueno):
    user, biz = dueno
    otra = Business.objects.create(name="Otra", kind="retail")
    Camera.objects.create(business=otra, name="Ajena", source="0")
    client.force_login(user)

    r = client.get(f"/api/camaras/?business={biz.pk}")

    assert not any(c["name"] == "Ajena" for c in r.data)
