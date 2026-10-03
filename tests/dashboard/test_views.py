import pytest
from django.contrib.auth.models import User

from tenancy.models import Business, Profile


@pytest.fixture
def world(db):
    a = Business.objects.create(name="Cafe Uno", kind="cafe")
    b = Business.objects.create(name="Tienda Dos", kind="retail")
    ana = User.objects.create_user("ana", password="secreto123")
    Profile.objects.create(user=ana, role="owner", business=a)
    root = User.objects.create_user("root", password="secreto123")
    Profile.objects.create(user=root, role="admin")
    return dict(a=a, b=b, ana=ana, root=root)


@pytest.mark.django_db
def test_anonymous_is_redirected_to_login(client, world):
    r = client.get("/")

    assert r.status_code == 302
    assert "/accounts/login/" in r["Location"]


@pytest.mark.django_db
def test_owner_sees_only_their_business(client, world):
    """`/` sirve el shell de React; qué negocio ve cada quien lo decide
    `/api/negocio-actual/`, ya probado en tests/tenancy/test_negocio_actual.py.
    Aquí solo se confirma que ese endpoint sigue filtrando por dueño."""
    client.force_login(world["ana"])

    r = client.get("/api/negocio-actual/")

    assert r.status_code == 200
    assert [n["nombre"] for n in r.data["negocios"]] == ["Cafe Uno"]


@pytest.mark.django_db
def test_admin_sees_every_business(client, world):
    client.force_login(world["root"])

    r = client.get("/api/negocio-actual/")
    nombres = {n["nombre"] for n in r.data["negocios"]}

    assert r.status_code == 200
    assert nombres == {"Cafe Uno", "Tienda Dos"}
