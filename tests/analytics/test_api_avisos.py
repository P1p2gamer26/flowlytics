from datetime import date, time

import pytest
from django.contrib.auth.models import User

from analytics.models import AlertRule, AlertDelivery
from cameras.models import Camera
from tenancy.models import Business, Profile


@pytest.fixture
def world(db):
    biz_a = Business.objects.create(name="A", kind="cafe", abre=time(8, 0), cierra=time(22, 0))
    biz_b = Business.objects.create(name="B", kind="retail")
    cam_a = Camera.objects.create(business=biz_a, name="ca", source="0")
    cam_b = Camera.objects.create(business=biz_b, name="cb", source="0")

    owner_a = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=owner_a, role="owner", business=biz_a)
    admin = User.objects.create_user("root", password="x")
    Profile.objects.create(user=admin, role="admin")
    return dict(biz_a=biz_a, biz_b=biz_b, owner_a=owner_a, admin=admin, cam_a=cam_a)


@pytest.mark.django_db
def test_avisos_get_returns_reglas_sugeridos_horario_recientes(api_client, world):
    biz_a = world["biz_a"]
    owner_a = world["owner_a"]

    AlertRule.objects.create(business=biz_a, tipo_evento="long_queue", canal="webhook",
                             destino="https://hook", umbral=300, minutos_silencio=15, activa=True)
    AlertRule.objects.create(business=biz_a, tipo_evento="empty_counter", canal="email",
                             destino="dueño@tienda.co", umbral=None, minutos_silencio=10, activa=False)

    AlertDelivery.objects.create(rule_id=1, mensaje="test", resultado="enviada", error="")

    api_client.force_authenticate(owner_a)
    r = api_client.get("/api/avisos/", {"business": biz_a.pk})

    assert r.status_code == 200
    data = r.json()
    assert "reglas" in data
    assert "sugeridos" in data
    assert "horario" in data
    assert "recientes" in data
    assert len(data["reglas"]) == 2
    assert data["horario"]["abre"] == "08:00"
    assert data["horario"]["cierra"] == "22:00"
    assert len(data["recientes"]) == 1


@pytest.mark.django_db
def test_avisos_post_creates_rule(api_client, world):
    biz_a = world["biz_a"]
    owner_a = world["owner_a"]
    api_client.force_authenticate(owner_a)

    r = api_client.post("/api/avisos/", {"business": biz_a.pk, "tipo_evento": "long_queue",
                                         "canal": "webhook", "destino": "https://hook",
                                         "umbral": 300, "minutos_silencio": 15})

    assert r.status_code == 201
    data = r.json()
    assert data["tipo_evento"] == "long_queue"
    assert data["canal"] == "webhook"
    assert data["destino"] == "https://hook"
    assert data["umbral"] == 300
    assert data["minutos_silencio"] == 15
    assert data["activa"] is True


@pytest.mark.django_db
def test_avisos_post_validates_choices_and_destino(api_client, world):
    biz_a = world["biz_a"]
    owner_a = world["owner_a"]
    api_client.force_authenticate(owner_a)

    r = api_client.post("/api/avisos/", {"business": biz_a.pk, "tipo_evento": "invalido",
                                         "canal": "webhook", "destino": "https://hook"})
    assert r.status_code == 400

    r = api_client.post("/api/avisos/", {"business": biz_a.pk, "tipo_evento": "long_queue",
                                         "canal": "invalido", "destino": "https://hook"})
    assert r.status_code == 400

    r = api_client.post("/api/avisos/", {"business": biz_a.pk, "tipo_evento": "long_queue",
                                         "canal": "webhook", "destino": ""})
    assert r.status_code == 400


@pytest.mark.django_db
def test_aviso_detalle_put_partial_update(api_client, world):
    biz_a = world["biz_a"]
    owner_a = world["owner_a"]
    api_client.force_authenticate(owner_a)

    regla = AlertRule.objects.create(business=biz_a, tipo_evento="long_queue", canal="webhook",
                                     destino="https://hook", umbral=300, minutos_silencio=15, activa=True)

    r = api_client.put(f"/api/avisos/{regla.pk}/", {"business": biz_a.pk,
                                                     "activa": False, "umbral": 600, "minutos_silencio": 20})
    assert r.status_code == 200
    data = r.json()
    assert data["activa"] is False
    assert data["umbral"] == 600
    assert data["minutos_silencio"] == 20


@pytest.mark.django_db
def test_aviso_detalle_put_validates_canal_and_destino(api_client, world):
    biz_a = world["biz_a"]
    owner_a = world["owner_a"]
    api_client.force_authenticate(owner_a)

    regla = AlertRule.objects.create(business=biz_a, tipo_evento="long_queue", canal="webhook",
                                     destino="https://hook", umbral=300)

    r = api_client.put(f"/api/avisos/{regla.pk}/", {"business": biz_a.pk,
                                                     "canal": "invalido"})
    assert r.status_code == 400

    r = api_client.put(f"/api/avisos/{regla.pk}/", {"business": biz_a.pk,
                                                     "destino": ""})
    assert r.status_code == 400


@pytest.mark.django_db
def test_aviso_detalle_delete_returns_204(api_client, world):
    biz_a = world["biz_a"]
    owner_a = world["owner_a"]
    api_client.force_authenticate(owner_a)

    regla = AlertRule.objects.create(business=biz_a, tipo_evento="long_queue", canal="webhook",
                                     destino="https://hook", umbral=300)

    r = api_client.delete(f"/api/avisos/{regla.pk}/", {"business": biz_a.pk})
    assert r.status_code == 204
    assert not AlertRule.objects.filter(pk=regla.pk).exists()


@pytest.mark.django_db
def test_aviso_detalle_404_if_not_own_business(api_client, world):
    biz_a = world["biz_a"]
    biz_b = world["biz_b"]
    owner_a = world["owner_a"]
    api_client.force_authenticate(owner_a)

    regla = AlertRule.objects.create(business=biz_b, tipo_evento="long_queue", canal="webhook",
                                     destino="https://hook", umbral=300)

    r = api_client.delete(f"/api/avisos/{regla.pk}/", {"business": biz_a.pk})
    assert r.status_code == 404


@pytest.mark.django_db
def test_aviso_horario_put_updates_business(api_client, world):
    biz_a = world["biz_a"]
    owner_a = world["owner_a"]
    api_client.force_authenticate(owner_a)

    r = api_client.put("/api/avisos/horario/", {"business": biz_a.pk, "abre": "09:30", "cierra": "21:45"})
    assert r.status_code == 200
    data = r.json()
    assert data["abre"] == "09:30"
    assert data["cierra"] == "21:45"
    biz_a.refresh_from_db()
    assert biz_a.abre == time(9, 30)
    assert biz_a.cierra == time(21, 45)


@pytest.mark.django_db
def test_aviso_horario_validates_format(api_client, world):
    biz_a = world["biz_a"]
    owner_a = world["owner_a"]
    api_client.force_authenticate(owner_a)

    r = api_client.put("/api/avisos/horario/", {"business": biz_a.pk, "abre": "9:30", "cierra": "21:45"})
    assert r.status_code == 400

    r = api_client.put("/api/avisos/horario/", {"business": biz_a.pk, "abre": "09:30"})
    assert r.status_code == 400


@pytest.mark.django_db
def test_owner_cannot_read_another_business_avisos(api_client, world):
    biz_a = world["biz_a"]
    biz_b = world["biz_b"]
    owner_a = world["owner_a"]
    api_client.force_authenticate(owner_a)

    r = api_client.get("/api/avisos/", {"business": biz_b.pk})
    assert r.status_code == 403


@pytest.mark.django_db
def test_admin_can_read_any_business_avisos(api_client, world):
    biz_b = world["biz_b"]
    admin = world["admin"]
    api_client.force_authenticate(admin)

    r = api_client.get("/api/avisos/", {"business": biz_b.pk})
    assert r.status_code == 200


@pytest.mark.django_db
def test_anonymous_is_rejected(api_client, world):
    biz_a = world["biz_a"]
    r = api_client.get("/api/avisos/", {"business": biz_a.pk})
    assert r.status_code in (401, 403)