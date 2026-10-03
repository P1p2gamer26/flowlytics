"""Bloqueo tras N intentos fallidos. El sistema estará expuesto a internet."""
from datetime import timedelta

from django.contrib.auth.backends import ModelBackend

UMBRAL = 5
VENTANA = timedelta(minutes=15)


def bloqueado(fallidos, umbral=UMBRAL):
    return fallidos >= umbral


class LockoutModelBackend(ModelBackend):
    """Niega la autenticación si el usuario acumuló demasiados fallos recientes."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        from django.utils import timezone

        from tenancy.models import IntentoLogin
        if username and bloqueado(
                IntentoLogin.fallidos_recientes(username, timezone.now(), VENTANA)):
            return None
        return super().authenticate(request, username=username, password=password, **kwargs)
