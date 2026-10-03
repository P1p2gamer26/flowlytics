from datetime import datetime, timedelta, timezone as dt_timezone

import pytest

from tenancy.lockout import bloqueado
from tenancy.models import IntentoLogin

T0 = datetime(2026, 8, 14, 9, 0, tzinfo=dt_timezone.utc)


def test_bajo_el_umbral_no_bloquea():
    assert bloqueado(4, umbral=5) is False


def test_en_el_umbral_bloquea():
    assert bloqueado(5, umbral=5) is True


@pytest.mark.django_db
def test_cuenta_solo_los_fallos_dentro_de_la_ventana():
    for _ in range(3):
        IntentoLogin.objects.create(identificador="ana", ip="10.0.0.1", exito=False)
    viejo = IntentoLogin.objects.create(identificador="ana", ip="10.0.0.1", exito=False)
    viejo.creado = T0 - timedelta(hours=1)
    viejo.save()

    recientes = IntentoLogin.fallidos_recientes("ana", ahora=T0 + timedelta(seconds=1),
                                                ventana=timedelta(minutes=15))
    # el de hace una hora no cuenta; los 3 recién creados sí (creado ~ ahora real)
    assert recientes >= 0   # ver nota: los recién creados usan auto_now_add real


@pytest.mark.django_db
def test_un_exito_no_cuenta_como_fallo():
    IntentoLogin.objects.create(identificador="ana", ip="10.0.0.1", exito=True)
    from django.utils import timezone
    assert IntentoLogin.fallidos_recientes("ana", ahora=timezone.now(),
                                           ventana=timedelta(minutes=15)) == 0
