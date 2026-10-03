from datetime import datetime, timedelta, timezone as dt_timezone

import pytest

from analytics.models import AlertRule, AlertDelivery, Event
from analytics.notifier import Notifier, NullBackend, notificar_evento
from cameras.models import Camera
from tenancy.models import Business

T0 = datetime(2026, 8, 14, 9, 0, tzinfo=dt_timezone.utc)


@pytest.fixture
def regla(db):
    biz = Business.objects.create(name="Cafe", kind="cafe")
    return AlertRule.objects.create(business=biz, tipo_evento="long_queue",
                                    canal="webhook", destino="https://hook.test/x",
                                    minutos_silencio=15)


class BackendFalla:
    def enviar(self, destino, mensaje):
        raise RuntimeError("canal caido")


@pytest.mark.django_db
def test_notifica_y_registra_la_entrega(regla):
    backend = NullBackend()
    notifier = Notifier(backend, ahora=lambda: T0)

    entrega = notifier.notificar(regla, "Fila larga en barra")

    assert entrega.resultado == "enviada"
    assert backend.enviados == [("https://hook.test/x", "Fila larga en barra")]
    regla.refresh_from_db()
    assert regla.ultima_notificacion == T0


@pytest.mark.django_db
def test_anti_spam_silencia_dentro_de_la_ventana(regla):
    backend = NullBackend()
    Notifier(backend, ahora=lambda: T0).notificar(regla, "1")
    regla.refresh_from_db()

    entrega = Notifier(backend, ahora=lambda: T0 + timedelta(minutes=5)).notificar(regla, "2")

    assert entrega.resultado == "silenciada"
    assert len(backend.enviados) == 1   # el segundo no salió


@pytest.mark.django_db
def test_pasada_la_ventana_vuelve_a_notificar(regla):
    backend = NullBackend()
    Notifier(backend, ahora=lambda: T0).notificar(regla, "1")
    regla.refresh_from_db()

    entrega = Notifier(backend, ahora=lambda: T0 + timedelta(minutes=20)).notificar(regla, "2")

    assert entrega.resultado == "enviada"
    assert len(backend.enviados) == 2


@pytest.mark.django_db
def test_fallo_del_canal_queda_registrado_y_no_marca_silencio(regla):
    entrega = Notifier(BackendFalla(), ahora=lambda: T0).notificar(regla, "1")

    assert entrega.resultado == "fallo"
    assert "canal caido" in entrega.error
    regla.refresh_from_db()
    assert regla.ultima_notificacion is None   # un fallo no arranca el anti-spam


@pytest.mark.django_db
def test_notificar_evento_dispara_las_reglas_del_negocio(regla):
    cam = Camera.objects.create(business=regla.business, name="Barra", source="0")
    from django.utils import timezone
    ev = Event.objects.create(camera=cam, kind="long_queue", zone_name="fila",
                              value=8, occurred_at=timezone.now())
    backend = NullBackend()

    notificar_evento(ev, notifier=Notifier(backend, ahora=lambda: T0))

    assert len(backend.enviados) == 1
    assert AlertDelivery.objects.filter(rule=regla, resultado="enviada").exists()
