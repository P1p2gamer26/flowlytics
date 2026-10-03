from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from cameras.models import Camera, CameraHealth
from tenancy.models import Business, Profile


@pytest.fixture
def dueno(db):
    biz = Business.objects.create(name="Cafe Uno", kind="cafe")
    cam = Camera.objects.create(business=biz, name="Barra", source="0")
    user = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=user, role="owner", business=biz)
    return user, biz, cam


@pytest.mark.django_db
def test_avisa_cuando_una_camara_lleva_rato_sin_latir(client, dueno):
    user, biz, cam = dueno
    CameraHealth.latir(cam, frames=1, reconexiones=0)
    salud = CameraHealth.objects.get(camera=cam)
    salud.ultimo_latido = timezone.now() - timedelta(hours=2)
    salud.save()
    client.force_login(user)

    r = client.get(f"/api/panel-extra/?business={biz.pk}")

    caidas = r.data["camaras_caidas"]
    assert len(caidas) == 1
    assert caidas[0]["camara"] == "Barra"


@pytest.mark.django_db
def test_no_avisa_si_la_camara_late(client, dueno):
    user, biz, cam = dueno
    CameraHealth.latir(cam, frames=100, reconexiones=0)
    client.force_login(user)

    r = client.get(f"/api/panel-extra/?business={biz.pk}")

    assert r.data["camaras_caidas"] == []
