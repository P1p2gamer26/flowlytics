"""El aviso sale por el canal que eligió el dueño y solo con el local abierto.

`locmem` (fijado en config/settings_test.py) garantiza que ninguna prueba abra
una conexión SMTP: el correo se queda en `django.core.mail.outbox`.
"""
from datetime import datetime, time, timezone as dt_tz

import pytest
from django.core import mail
from django.utils import timezone

from analytics.models import AlertRule, Event
from analytics.notifier import (EmailBackend, Notifier, WebhookBackend,
                                backend_de, notificar_evento)

ABIERTO = datetime(2026, 9, 9, 15, 0, tzinfo=dt_tz.utc)   # 10:00 en Bogotá
CERRADO = datetime(2026, 9, 9, 8, 0, tzinfo=dt_tz.utc)    # 03:00 en Bogotá


@pytest.fixture
def regla_correo(camara_demo):
    negocio = camara_demo.business
    negocio.abre, negocio.cierra = time(8), time(20)
    negocio.save()
    return AlertRule.objects.create(business=negocio, tipo_evento="long_queue",
                                    canal="email", destino="dueno@tienda.co")


@pytest.mark.django_db
def test_el_aviso_por_correo_sale_por_el_backend_de_django(regla_correo):
    entrega = Notifier(EmailBackend(), ahora=lambda: ABIERTO).notificar(
        regla_correo, "Fila larga en Caja 1: la espera llegó a 6 min")

    assert entrega.resultado == "enviada"
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["dueno@tienda.co"]
    assert "6 min" in mail.outbox[0].body


@pytest.mark.django_db
def test_con_el_local_cerrado_no_se_manda_nada_pero_queda_registrado(regla_correo):
    entrega = Notifier(EmailBackend(), ahora=lambda: CERRADO).notificar(
        regla_correo, "Fila larga a las 3 de la mañana")

    assert entrega.resultado == "fuera_hora"
    assert mail.outbox == []
    # Y no gasta el anti-spam: si a las 8:00 hay fila de verdad, se avisa.
    regla_correo.refresh_from_db()
    assert regla_correo.ultima_notificacion is None


@pytest.mark.django_db
def test_el_canal_de_la_regla_decide_el_backend(regla_correo):
    assert isinstance(backend_de(regla_correo), EmailBackend)

    regla_correo.canal = "webhook"
    assert isinstance(backend_de(regla_correo), WebhookBackend)


@pytest.mark.django_db
def test_notificar_evento_manda_por_correo_sin_que_nadie_le_pase_backend(camara_demo):
    # Horario por defecto (abre == cierra): a cualquier hora, para que el test
    # no dependa de la hora a la que se corra la suite.
    AlertRule.objects.create(business=camara_demo.business, tipo_evento="long_queue",
                             canal="email", destino="dueno@tienda.co")
    evento = Event.objects.create(camera=camara_demo, kind="long_queue",
                                  zone_name="Caja 1", value=360.0,
                                  occurred_at=timezone.now())

    notificar_evento(evento)

    assert len(mail.outbox) == 1
    assert "Caja 1" in mail.outbox[0].body
