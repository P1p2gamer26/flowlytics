import pytest
from django.contrib.auth.models import User

from tenancy.admin import AuditLogAdmin
from tenancy.models import AuditLog


class _Req:
    def __init__(self, user, ip="10.0.0.9"):
        self.user = user
        self.META = {"REMOTE_ADDR": ip}


@pytest.mark.django_db
def test_registrar_guarda_usuario_accion_e_ip():
    ana = User.objects.create_user("ana", password="x")
    AuditLog.registrar(_Req(ana), "ver_clip", objeto="Event#3")

    fila = AuditLog.objects.get()
    assert fila.usuario == ana
    assert fila.accion == "ver_clip"
    assert fila.objeto == "Event#3"
    assert fila.ip == "10.0.0.9"


@pytest.mark.django_db
def test_usuario_anonimo_queda_como_nulo():
    from django.contrib.auth.models import AnonymousUser
    AuditLog.registrar(_Req(AnonymousUser()), "login_fallido")
    assert AuditLog.objects.get().usuario is None


@pytest.mark.django_db
def test_el_admin_no_permite_borrar():
    # la auditoría no se borra desde la aplicación
    assert AuditLogAdmin(AuditLog, None).has_delete_permission(_Req(None)) is False
