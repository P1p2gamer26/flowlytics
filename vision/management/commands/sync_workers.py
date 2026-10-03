"""Arranca/para las units de cámara según la tabla Camera.

`systemctl start vision-camera@3` corre `manage.py run_camera 3`. Así agregar una
cámara desde el dashboard la pone a correr sin SSH. El ejecutor se inyecta; en
tests se pasa un doble que registra las llamadas en vez de tocar systemd.
"""
import subprocess

from django.core.management.base import BaseCommand


def unidad(cam_id):
    return f"vision-camera@{cam_id}.service"


def sincronizar(ids_habilitadas, executor):
    deseadas = {unidad(i) for i in ids_habilitadas}
    actuales = executor.activas()
    for u in deseadas - actuales:
        executor.arrancar(u)
    for u in actuales - deseadas:
        executor.parar(u)
    return deseadas


class SystemctlExecutor:
    def activas(self):
        out = subprocess.run(
            ["systemctl", "list-units", "--type=service", "--state=running",
             "--no-legend", "vision-camera@*"],
            capture_output=True, text=True,
        ).stdout
        return {line.split()[0] for line in out.splitlines() if line.strip()}

    def arrancar(self, unit):
        subprocess.run(["systemctl", "start", unit], check=True)

    def parar(self, unit):
        subprocess.run(["systemctl", "stop", unit], check=True)


class Command(BaseCommand):
    help = "Sincroniza las units systemd de cámara con la tabla Camera."

    def handle(self, *args, **opts):
        from cameras.models import Camera
        ids = list(Camera.objects.filter(enabled=True).values_list("pk", flat=True))
        deseadas = sincronizar(ids, SystemctlExecutor())
        self.stdout.write(self.style.SUCCESS(f"{len(deseadas)} cámaras sincronizadas."))
