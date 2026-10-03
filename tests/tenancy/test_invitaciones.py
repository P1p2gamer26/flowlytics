import pytest
from django.contrib.auth.models import User

from tenancy.models import Business, Invitation, Profile


@pytest.fixture
def duena(db):
    biz = Business.objects.create(name="Neg", kind="cafe")
    user = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=user, role="owner", business=biz)
    return user, biz


@pytest.mark.django_db
def test_invitation_genera_token_unico():
    biz = Business.objects.create(name="N", kind="cafe")
    a = Invitation.objects.create(business=biz, email="a@x.com")
    b = Invitation.objects.create(business=biz, email="b@x.com")
    assert a.token and b.token and a.token != b.token


@pytest.mark.django_db
def test_duena_crea_invitacion_para_su_negocio(client, duena):
    user, biz = duena
    client.force_login(user)
    r = client.post("/invitar/", {"email": "nuevo@x.com"})
    assert r.status_code in (200, 302)
    assert Invitation.objects.filter(business=biz, email="nuevo@x.com").exists()


@pytest.mark.django_db
def test_aceptar_invitacion_crea_usuario_en_ese_negocio(client, duena):
    _, biz = duena
    inv = Invitation.objects.create(business=biz, email="nuevo@x.com")

    r = client.post(f"/invitacion/{inv.token}/",
                    {"username": "nuevo", "password": "clave-larga-123"})

    assert r.status_code == 302
    perfil = Profile.objects.get(user__username="nuevo")
    assert perfil.business == biz
    inv.refresh_from_db()
    assert inv.aceptada is True


@pytest.mark.django_db
def test_token_ya_aceptado_no_se_reutiliza(client, duena):
    _, biz = duena
    inv = Invitation.objects.create(business=biz, email="x@x.com", aceptada=True)
    r = client.post(f"/invitacion/{inv.token}/",
                    {"username": "tarde", "password": "clave-larga-123"})
    assert r.status_code == 404
    assert not User.objects.filter(username="tarde").exists()
