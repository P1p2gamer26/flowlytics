"""¿Quedó bien puesto? Los chequeos que se corren después de desplegar.

Cada uno devuelve un Chequeo(nombre, ok, detalle, critico). Crítico es lo que
deja el sistema inservible; el resto informa (una máquina de desarrollo no tiene
systemd y eso no es un fallo del despliegue).

Lo que toca la red (/salud/) y systemd entra como función inyectada, igual que
el executor de sync_workers: la suite no abre sockets ni llama a systemctl.
"""
import os
from collections import namedtuple
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.db import connection

from config.validate import avisos_config, revisar_config

Chequeo = namedtuple("Chequeo", "nombre ok detalle critico")

UNIDAD_WEB = "vision-web.service"


def _base():
    motor = settings.DATABASES["default"]["ENGINE"].rsplit(".", 1)[-1]
    try:
        connection.cursor().execute("SELECT 1")
        return Chequeo("base", True, f"{motor} responde", True)
    except Exception as exc:
        return Chequeo("base", False, f"{motor}: {exc}"[:150], True)


def _migraciones():
    try:
        call_command("migrate", "--check", "--noinput", verbosity=0)
        return Chequeo("migraciones", True, "al día", True)
    except SystemExit:
        return Chequeo("migraciones", False, "faltan migraciones: corre manage.py migrate", True)


def _configuracion():
    problemas = revisar_config(settings)
    detalle = " | ".join(problemas + avisos_config(settings)) or "sin problemas"
    return Chequeo("configuración", not problemas, detalle[:400], True)


def _estaticos():
    raiz = Path(getattr(settings, "STATIC_ROOT", "") or ".")
    hay = raiz.is_dir() and any(raiz.iterdir())
    detalle = str(raiz) if hay else f"{raiz} vacío: falta collectstatic"
    return Chequeo("estáticos", hay, detalle, not settings.DEBUG)


def _media():
    raiz = Path(settings.MEDIA_ROOT)
    ok = raiz.is_dir() and os.access(raiz, os.W_OK)
    return Chequeo("media", ok, f"{raiz} {'escribible' if ok else 'no escribible'}", True)


def _web(lector_salud):
    try:
        datos = lector_salud()
    except Exception as exc:
        return Chequeo("web", False, f"/salud/ no responde: {exc}"[:150], True)
    ok = bool(datos.get("db"))
    return Chequeo("web", ok, f"/salud/ db={datos.get('db')} versión={datos.get('version')}", True)


def _unidad(estado_unidad):
    estado = estado_unidad(UNIDAD_WEB)
    return Chequeo("unidad web", estado == "active", f"{UNIDAD_WEB}: {estado}", False)


def _camaras():
    from cameras.models import Camera, CameraHealth

    habilitadas = set(Camera.objects.filter(enabled=True).values_list("pk", flat=True))
    vivas = {s.camera_id for s in CameraHealth.objects.all() if s.esta_viva()}
    sin_latido = sorted(habilitadas - vivas)
    detalle = f"{len(habilitadas & vivas)}/{len(habilitadas)} con latido fresco"
    if sin_latido:
        detalle += f"; sin latido: {sin_latido}"
    return Chequeo("cámaras", not sin_latido, detalle, False)


def verificar(lector_salud, estado_unidad):
    """Corre los ocho chequeos en orden de "sin esto no sigue nada"."""
    return [
        _base(),
        _migraciones(),
        _configuracion(),
        _estaticos(),
        _media(),
        _web(lector_salud),
        _unidad(estado_unidad),
        _camaras(),
    ]


def formatear(chequeos):
    lineas = [f"{'✓' if c.ok else '✗'} {c.nombre:<14} {c.detalle}" for c in chequeos]
    verdes = sum(1 for c in chequeos if c.ok)
    criticos = [c.nombre for c in chequeos if not c.ok and c.critico]
    cierre = f"\n{verdes}/{len(chequeos)} en verde"
    cierre += f"; crítico mal: {', '.join(criticos)}." if criticos else "."
    return "\n".join(lineas) + cierre
