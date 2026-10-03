"""Lanzar el worker de una cámara desde la web y mirar cómo va.

El worker sigue siendo un proceso aparte: aquí no se procesa nada, solo se
arranca. `ejecutar` se inyecta en los tests para no lanzar procesos de verdad.

ponytail: un subprocess suelto, sin cola de tareas. Aguanta la demo y un par de
videos a la vez. Cuando haya que encolar, reintentar o cancelar, esto pide
Celery o django-q — no más banderas aquí.
"""
import subprocess
import sys

from analytics.models import Event, MetricWindow
from cameras.models import CameraHealth


def _ejecutar(cmd):
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def lanzar(camera, segundos=None, ejecutar=None):
    if not camera.zones.exists():
        raise ValueError("La cámara no tiene ninguna zona dibujada todavía.")

    cmd = [sys.executable, "manage.py", "run_camera", str(camera.pk), "--una-pasada"]
    if segundos:
        cmd += ["--max-seconds", str(segundos)]
    (ejecutar or _ejecutar)(cmd)


def progreso(camera):
    salud = CameraHealth.objects.filter(camera=camera).first()
    return {
        "ventanas": MetricWindow.objects.filter(camera=camera).count(),
        "eventos": Event.objects.filter(camera=camera).count(),
        "viva": bool(salud and salud.esta_viva()),
        "ultimo_latido": salud.ultimo_latido.isoformat() if salud else None,
        "reconexiones": salud.reconexiones if salud else 0,
        "ultimo_error": salud.ultimo_error if salud else "",
    }
