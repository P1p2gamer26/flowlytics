import pytest
from django.contrib.auth.models import User

from cameras.models import Camera, Zone
from tenancy.models import Business, Profile


@pytest.fixture
def duena(db):
    biz = Business.objects.create(name="Neg", kind="cafe")
    user = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=user, role="owner", business=biz)
    return user, biz


@pytest.mark.django_db
def test_onboarding_pide_login(client):
    r = client.get("/onboarding/")
    assert r.status_code == 302 and "/accounts/login" in r.url


@pytest.mark.django_db
def test_onboarding_marca_camara_pendiente_sin_camaras(client, duena):
    user, _ = duena
    client.force_login(user)
    r = client.get("/onboarding/")
    assert r.status_code == 200
    assert r.context["tiene_camara"] is False
    assert r.context["tiene_zona"] is False


@pytest.mark.django_db
def test_onboarding_marca_pasos_hechos_cuando_existen(client, duena):
    user, biz = duena
    cam = Camera.objects.create(business=biz, name="c", source="0")
    Zone.objects.create(camera=cam, name="z", kind="general", polygon=[[0, 0], [1, 0], [1, 1]])
    client.force_login(user)
    r = client.get("/onboarding/")
    assert r.context["tiene_camara"] is True
    assert r.context["tiene_zona"] is True
