import pytest
from django.contrib.auth.models import User

from cameras.models import Camera
from tenancy.models import Business, Plan, Profile


@pytest.mark.django_db
def test_no_admin_no_entra(client):
    biz = Business.objects.create(name="Neg", kind="cafe")
    user = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=user, role="owner", business=biz)
    client.force_login(user)
    assert client.get("/plataforma/").status_code == 403


@pytest.mark.django_db
def test_admin_ve_todos_los_negocios_con_metricas(client):
    plan = Plan.objects.create(nombre="Pro", max_camaras=5)
    biz_a = Business.objects.create(name="Alfa", kind="cafe", plan=plan)
    biz_b = Business.objects.create(name="Beta", kind="retail")
    Camera.objects.create(business=biz_a, name="c", source="0")

    admin = User.objects.create_user("root", password="x")
    Profile.objects.create(user=admin, role="admin")
    client.force_login(admin)

    r = client.get("/plataforma/")
    assert r.status_code == 200
    filas = {f["business"].name: f for f in r.context["filas"]}
    assert set(filas) == {"Alfa", "Beta"}
    assert filas["Alfa"]["num_camaras"] == 1
    assert filas["Alfa"]["plan"] == "Pro"
    assert filas["Beta"]["plan"] == "(sin plan)"
