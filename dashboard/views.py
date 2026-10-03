import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render

from analytics.models import JobRun, MetricWindow
from cameras.models import CameraHealth


@login_required
def sistema(request):
    perfil = getattr(request.user, "profile", None)
    if perfil is None or not perfil.is_admin:
        raise PermissionDenied("Solo administradores de la plataforma.")

    return render(request, "dashboard/sistema.html", {
        "workers": CameraHealth.objects.select_related("camera"),
        "jobs": JobRun.objects.all(),
        "fps_objetivo": settings.SAMPLE_FPS,
        "ventanas_degradadas": MetricWindow.objects.filter(degradada=True).count(),
    })


@login_required
def app_shell(request, resto=""):
    """Una sola plantilla para todas las rutas del front: el enrutado lo hace
    React. `resto` se ignora aquí a propósito."""
    return render(request, "dashboard/app.html")


def salud(request):
    """Estado operativo, sin autenticación y sin datos de negocio: lo consulta
    el watchdog y lo abre Julián desde el celular."""
    try:
        connection.cursor().execute("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False

    workers = [
        {"camara_id": s.camera_id, "viva": s.esta_viva(),
         "ultimo_latido": s.ultimo_latido.isoformat()}
        for s in CameraHealth.objects.all()
    ]
    jobs = {j.nombre: {"ok": j.ok, "terminado_en": j.terminado_en.isoformat()}
            for j in JobRun.objects.all()}

    return JsonResponse({
        "db": db_ok,
        "workers": workers,
        "jobs": jobs,
        "version": os.getenv("APP_VERSION", "dev"),
    })
