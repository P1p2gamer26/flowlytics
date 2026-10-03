import pytest
from django.contrib.auth.models import User

from cameras.models import Camera
from tenancy.models import Business, Plan, Profile


@pytest.fixture
def duena_con_plan_chico(db):
    plan = Plan.objects.create(nombre="Chico", max_camaras=1)
    biz = Business.objects.create(name="Tope", kind="cafe", plan=plan)
    user = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=user, role="owner", business=biz)
    return user, biz


@pytest.mark.django_db
def test_crear_camara_dentro_del_limite_funciona(api_client, duena_con_plan_chico):
    user, biz = duena_con_plan_chico
    api_client.force_authenticate(user)
    r = api_client.post("/api/camaras/", {"business": biz.pk, "name": "c1", "source": "0"})
    assert r.status_code == 201


@pytest.mark.django_db
def test_crear_camara_pasado_el_limite_devuelve_402(api_client, duena_con_plan_chico):
    user, biz = duena_con_plan_chico
    Camera.objects.create(business=biz, name="c1", source="0")   # ya en el tope
    api_client.force_authenticate(user)
    r = api_client.post("/api/camaras/", {"business": biz.pk, "name": "c2", "source": "0"})
    assert r.status_code == 402
    assert not Camera.objects.filter(business=biz, name="c2").exists()
