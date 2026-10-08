import json
from datetime import time

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from analytics.avisos_demo import sembrar_avisos
from analytics.models import AlertDelivery, AlertRule, Event
from analytics.notifier import notificar_evento
from cameras.models import Camera
from tenancy.models import Business, Profile


pytestmark = pytest.mark.django_db


@pytest.fixture
def mundo(db):
    a = Business.objects.create(name="A", kind="retail", abre=time(0, 0), cierra=time(0, 0))
    b = Business.objects.create(name="B", kind="retail")
    Camera.objects.create(business=a, name="Caja", source="0")
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    return dict(a=a, b=b, ana=ana)


def test_accion_operativa_queda_registrada_con_su_texto(mundo):
    AlertRule.objects.create(business=mundo["a"], tipo_evento="long_queue", accion="abrir_caja")
    cam = Camera.objects.get(business=mundo["a"])
    ev = Event.objects.create(camera=cam, kind="long_queue", zone_name="Fila", value=300,
                              occurred_at=timezone.now())

    entregas = notificar_evento(ev)

    assert entregas[0].resultado == "registrada"
    assert "abra la segunda caja" in entregas[0].mensaje
    assert entregas[0].camara == "Caja"


def test_simular_dispara_la_regla_y_se_repite(api_client, mundo):
    AlertRule.objects.create(business=mundo["a"], tipo_evento="long_queue", accion="mensaje_personal",
                             texto="Refuerza la caja")
    api_client.force_authenticate(mundo["ana"])
    url = f"/api/avisos/simular/?business={mundo['a'].pk}"

    for _ in range(2):   # el silencio de 15 min no debe frenar la demo
        r = api_client.post(url, {"tipo_evento": "long_queue"}, format="json")
        assert r.status_code == 201
        assert r.json()["entregas"][0]["resultado"] == "registrada"
        assert r.json()["entregas"][0]["simulado"] is True

    recientes = api_client.get(f"/api/avisos/?business={mundo['a'].pk}").json()["recientes"]
    assert len(recientes) == 2 and recientes[0]["camara"] == "Caja"


def test_simular_sin_reglas_lo_dice(api_client, mundo):
    api_client.force_authenticate(mundo["ana"])
    r = api_client.post(f"/api/avisos/simular/?business={mundo['a'].pk}", {}, format="json")
    assert r.status_code == 201 and r.json()["sin_reglas"] is True


def test_no_se_puede_simular_ni_crear_en_negocio_ajeno(api_client, mundo):
    api_client.force_authenticate(mundo["ana"])
    assert api_client.post(f"/api/avisos/simular/?business={mundo['b'].pk}", {}, format="json").status_code == 403
    assert api_client.post(f"/api/avisos/?business={mundo['b'].pk}",
                           {"tipo_evento": "long_queue", "accion": "registrar"},
                           format="json").status_code == 403
    assert api_client.get(f"/api/avisos/?business={mundo['b'].pk}").status_code == 403


def test_regla_operativa_no_pide_destino(api_client, mundo):
    api_client.force_authenticate(mundo["ana"])
    r = api_client.post(f"/api/avisos/?business={mundo['a'].pk}",
                        {"tipo_evento": "entry_peak", "accion": "registrar", "canal": "webhook"},
                        format="json")
    assert r.status_code == 201 and r.json()["accion"] == "registrar"


def test_sembrar_avisos_es_idempotente(mundo):
    sembrar_avisos(mundo["a"])
    sembrar_avisos(mundo["a"])
    assert AlertRule.objects.filter(business=mundo["a"]).count() == 3
    assert AlertDelivery.objects.filter(rule__business=mundo["a"]).count() >= 6


def test_seed_demo_deja_reglas_y_avisos():
    call_command("seed_demo", "--dias", "1")
    assert AlertRule.objects.filter(business__name="Demo").count() == 3


@pytest.mark.django_db
def test_sin_cuenta_puede_guardar_un_aviso_en_demo(settings):
    """Regresión del 403: el panel lee la cookie csrftoken con JS para mandar
    X-CSRFToken; si la cookie es HttpOnly el POST/PUT/DELETE siempre da 403."""
    settings.SIN_CUENTA = True
    call_command("seed_demo", "--dias", "1")
    demo = Business.objects.get(name="Demo")
    c = Client(enforce_csrf_checks=True)

    assert c.get(f"/api/avisos/?business={demo.pk}").status_code == 200
    cookie = c.cookies["csrftoken"]
    assert not cookie["httponly"]

    cuerpo = json.dumps({"tipo_evento": "long_queue", "canal": "email", "destino": "a@b.co", "umbral": 300})
    r = c.post(f"/api/avisos/?business={demo.pk}", cuerpo, content_type="application/json",
               HTTP_X_CSRFTOKEN=cookie.value)
    assert r.status_code == 201
    # y sin el token sigue siendo 403: la protección CSRF no se apagó
    assert c.post(f"/api/avisos/?business={demo.pk}", cuerpo,
                  content_type="application/json").status_code == 403
