"""Redacción de credenciales en logs y request_id por petición.

`redactar` borra la contraseña de cualquier URL con credenciales embebidas
(rtsp://usuario:password@host y similares) antes de que llegue al archivo.
"""
import logging
import re
from contextvars import ContextVar

_CRED = re.compile(r"(://[^:/@\s]+):[^@/\s]+@")
request_id_var = ContextVar("request_id", default="-")


def redactar(texto):
    return _CRED.sub(r"\1:***@", str(texto))


class RedactorDeCredenciales(logging.Filter):
    def filter(self, record):
        record.msg = redactar(record.getMessage())
        record.args = ()
        return True


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_var.get()
        return True
