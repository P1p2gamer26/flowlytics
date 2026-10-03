"""Supervisa workers de cámaras: un subproceso run_camera por cada cámara enabled con zonas.

`python manage.py correr_camaras` arranca, vigila y relanza los trabajadores.
Cada 60 s relee la BD (arranca nuevas, para deshabilitadas/borradas).
Si un subproceso termina, lo relanza a los 30 s.
Logs en logs/camara_<id>.log. Ctrl-C para todos los hijos.
"""
import logging
import os
import signal
import subprocess
import sys
import time
import traceback
from pathlib import Path

from django.core.management.base import BaseCommand

from cameras.models import Camera


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def planificar(deseadas: set[int], vivas: dict[int, subprocess.Popen]) -> tuple[set[int], set[int]]:
    """Decide qué cámaras arrancar y cuáles parar.

    Args:
        deseadas: IDs de cámaras que deberían estar corriendo (enabled + zonas).
        vivas: Diccionario {camera_id: proceso} de workers vivos actualmente.

    Returns:
        (arrancar, parar): conjuntos de camera_ids.
    """
    ids_vivas = set(vivas.keys())
    arrancar = deseadas - ids_vivas
    parar = ids_vivas - deseadas
    return arrancar, parar


class Command(BaseCommand):
    help = "Supervisa un worker run_camera por cada cámara enabled con zonas."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._procesos: dict[int, subprocess.Popen] = {}
        self._ultimo_relectura = 0.0
        self._fallidos: dict[int, float] = {}  # camera_id -> timestamp de cuando falló
        self._corriendo = True

    def add_arguments(self, parser):
        parser.add_argument(
            "--intervalo-relectura", type=int, default=60,
            help="Segundos entre relecturas de la tabla de cámaras (default: 60)."
        )
        parser.add_argument(
            "--reintento-caida", type=int, default=30,
            help="Segundos antes de relanzar un worker caído (default: 30)."
        )

    def handle(self, *args, **opts):
        self._configurar_seniales()
        intervalo = opts["intervalo_relectura"]
        reintento = opts["reintento_caida"]

        self.stdout.write("Iniciando supervisor de cámaras. Ctrl-C para detener.")

        try:
            while self._corriendo:
                ahora = time.monotonic()
                # Un error pasajero (p. ej. la base ocupada) no puede tumbar al
                # supervisor: se registra y se sigue. El 3-oct murió callado y
                # con él todas las cámaras.
                try:
                    if ahora - self._ultimo_relectura >= intervalo:
                        self._releer_y_planificar()
                        self._ultimo_relectura = ahora
                    self._revisar_procesos(ahora, reintento)
                except Exception:
                    self.stderr.write(f"[{time.strftime('%F %T')}] error en el supervisor, sigo:\n"
                                      f"{traceback.format_exc()}")

                # 3. Pequeña pausa para no consumir CPU
                time.sleep(1)

        except KeyboardInterrupt:
            pass
        finally:
            self._parar_todos()
            self.stdout.write("Supervisor detenido.")

    def _configurar_seniales(self):
        def manejar_senal(signum, frame):
            self._corriendo = False
        signal.signal(signal.SIGINT, manejar_senal)
        signal.signal(signal.SIGTERM, manejar_senal)
        if hasattr(signal, "SIGBREAK"):  # Windows
            signal.signal(signal.SIGBREAK, manejar_senal)

    def _releer_y_planificar(self):
        """Lee la BD y ajusta los workers según lo que toca."""
        deseadas = self._cams_deseadas()
        arrancar, parar = planificar(deseadas, self._procesos)

        for cam_id in parar:
            self._parar_worker(cam_id, "cámara deshabilitada o borrada")

        for cam_id in arrancar:
            self._arrancar_worker(cam_id)

        # Limpiar _fallidos de cámaras que ya no se desean
        for cam_id in list(self._fallidos.keys()):
            if cam_id not in deseadas:
                del self._fallidos[cam_id]

    def _cams_deseadas(self) -> set[int]:
        """IDs de cámaras que deberían tener worker: enabled=True y al menos una zona."""
        return set(
            Camera.objects.filter(enabled=True, zones__isnull=False)
            .distinct()
            .values_list("pk", flat=True)
        )

    def _arrancar_worker(self, cam_id: int):
        """Lanza run_camera <cam_id> como subproceso."""
        log_file = LOG_DIR / f"camara_{cam_id}.log"
        # Abrir en modo append, sin buffer (line buffered por defecto en texto)
        f = log_file.open("a", encoding="utf-8", buffering=1)

        args = [
            sys.executable, "manage.py", "run_camera", str(cam_id),
        ]
        # Añadir --tiempo-real para archivos
        cam = Camera.objects.filter(pk=cam_id).first()
        if cam and cam.es_video:
            args.append("--tiempo-real")

        try:
            proc = subprocess.Popen(
                args,
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd=Path.cwd(),
            )
            self._procesos[cam_id] = proc
            self.stdout.write(f"[{time.strftime('%F %T')}] Arrancado worker cámara {cam_id} (PID {proc.pid}) -> {log_file}")
        except Exception as exc:
            f.close()
            self.stderr.write(f"No se pudo arrancar cámara {cam_id}: {exc}")

    def _parar_worker(self, cam_id: int, motivo: str = ""):
        """Mata el subproceso de una cámara."""
        proc = self._procesos.pop(cam_id, None)
        if proc is None:
            return
        self.stdout.write(f"Parando cámara {cam_id} ({motivo})...")
        try:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
        except Exception as exc:
            self.stderr.write(f"Error parando cámara {cam_id}: {exc}")

    def _revisar_procesos(self, ahora: float, reintento: int):
        """Comprueba si algún worker murió y agenda relanzamiento."""
        for cam_id, proc in list(self._procesos.items()):
            if proc.poll() is not None:
                # Proceso terminó
                codigo = proc.returncode
                self.stdout.write(f"[{time.strftime('%F %T')}] Worker cámara {cam_id} terminó (código {codigo}).")
                del self._procesos[cam_id]
                self._fallidos[cam_id] = ahora

        # Relanzar caídos tras el tiempo de espera
        for cam_id, ts in list(self._fallidos.items()):
            if ahora - ts >= reintento:
                # La relectura periódica puede haberla relanzado ya: no duplicar.
                if cam_id not in self._procesos and cam_id in self._cams_deseadas():
                    self.stdout.write(f"[{time.strftime('%F %T')}] Relanzando cámara {cam_id} tras caída...")
                    self._arrancar_worker(cam_id)
                del self._fallidos[cam_id]

    def _parar_todos(self):
        """Para todos los workers al salir."""
        self.stdout.write("Parando todos los workers...")
        for cam_id in list(self._procesos.keys()):
            self._parar_worker(cam_id, "apagado del supervisor")