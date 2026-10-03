import pytest
from django.contrib.auth.models import User

from tenancy.models import Business, Profile


@pytest.mark.django_db
def test_registro_crea_usuario_negocio_y_perfil_dueno(client):
    r = client.post("/registro/", {
        "username": "nueva_duena", "password": "clave-larga-123",
        "nombre_negocio": "Mi Café", "kind": "cafe",
    })

    assert r.status_code == 302
    user = User.objects.get(username="nueva_duena")
    biz = Business.objects.get(name="Mi Café")
    perfil = Profile.objects.get(user=user)
    assert perfil.role == "owner"
    assert perfil.business == biz


@pytest.mark.django_db
def test_registro_inicia_sesion_y_redirige_al_onboarding(client):
    r = client.post("/registro/", {
        "username": "otra", "password": "clave-larga-123",
        "nombre_negocio": "Tienda", "kind": "retail",
    })
    assert r.url == "/onboarding/"
    # sesión iniciada: el onboarding no rebota al login
    assert client.get("/onboarding/").status_code == 200


@pytest.mark.django_db
def test_registro_rechaza_usuario_duplicado(client):
    User.objects.create_user("ocupado", password="x")
    r = client.post("/registro/", {
        "username": "ocupado", "password": "clave-larga-123",
        "nombre_negocio": "X", "kind": "cafe",
    })
    assert r.status_code == 200                      # re-muestra el form con error
    assert Business.objects.filter(name="X").count() == 0   # no dejó negocio huérfano
