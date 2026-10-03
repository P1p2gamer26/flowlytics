"""Chequeo post-despliegue: ¿esto quedó bien puesto?

Sale con código 1 si algo crítico está mal, para que deploy.sh se entere y no
diga "OK" sobre un sitio caído. Lo que toca la red y systemd vive aquí, en
funciones de módulo, para que los tests las reemplacen.
"""
import json
import subprocess
import urllib.request

from django.core.management.base import BaseCommand, CommandError

from dashboard.verificacion import formatear, verificar

URL_SALUD = "http://127.0.0.1:8000/salud/"


def leer_salud(url):
    with urllib.request.urlopen(url, timeout=5) as respuesta:
        return json.loads(respuesta.read().decode())


def estado_unidad(nombre):
    try:
        salida = subprocess.run(["systemctl", "is-active", nombre],
                                capture_output=True, text=True, timeout=10)
        return salida.stdout.strip() or "desconocido"
    except (OSError, subprocess.SubprocessError):
        return "sin systemd"


class Command(BaseCommand):
    help = "Verifica un despliegue: base, migraciones, configuración, estáticos, web y workers."

    def add_arguments(self, parser):
        parser.add_argument("--url", default=URL_SALUD,
                            help=f"dónde consultar /salud/ (por defecto {URL_SALUD})")

    def handle(self, *args, **opts):
        chequeos = verificar(lambda: leer_salud(opts["url"]), estado_unidad)
        self.stdout.write(formatear(chequeos))
        malos = [c.nombre for c in chequeos if not c.ok and c.critico]
        if malos:
            raise CommandError(f"Despliegue incompleto: {', '.join(malos)}.")
