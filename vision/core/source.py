"""Fuente de frames tolerante a fallos.

Una cámara RTSP real se cae, se reconecta y a veces devuelve basura. Un archivo
de video es una cámara sin red: se rebobina con `loop` o se agota y cierra. Este
módulo encapsula ambas realidades para que el pipeline no tenga que saberlo.

`abrir` y `dormir` se inyectan para poder testear reconexión y backoff sin
cámara y sin esperar segundos de verdad.
"""
import os
import time
from urllib.parse import unquote, urlparse

import cv2

from config.logging_filters import redactar

BACKOFF_MAX = 30.0


def es_fuente_archivo(source):
    """True si `source` apunta a un archivo de video local.

    Un `file://` o una ruta que existe en disco se trata como video. "0" es
    webcam y cualquier URL (rtsp/http) no es un archivo.
    """
    if not isinstance(source, str) or source == "0":
        return False
    if source.startswith("file://"):
        return True
    return os.path.exists(source)


def ruta_archivo(source):
    """Devuelve la ruta del archivo, quitando el prefijo `file://` si lo tiene."""
    if isinstance(source, str) and source.startswith("file://"):
        return unquote(source[len("file://"):])
    return source


class FuenteFalsa:
    """Doble de una captura de OpenCV. Un None en el guion simula fallo de lectura."""

    def __init__(self, guion, fps=2.0, ancho=4, alto=4):
        self._guion = list(guion)
        self._i = 0
        self.liberada = False
        self._fps = fps
        self._ancho = ancho
        self._alto = alto

    def read(self):
        if self._i >= len(self._guion):
            return False, None
        item = self._guion[self._i]
        self._i += 1
        return (item is not None), item

    def get(self, prop):
        if prop == cv2.CAP_PROP_FPS:
            return self._fps
        if prop == cv2.CAP_PROP_FRAME_WIDTH:
            return self._ancho
        if prop == cv2.CAP_PROP_FRAME_HEIGHT:
            return self._alto
        return 0.0

    def set(self, prop, valor):
        if prop == cv2.CAP_PROP_POS_FRAMES:
            self._i = 0
            return True
        return False

    def grab(self):
        """Avanza al siguiente frame sin devolverlo (simula cap.grab())."""
        if self._i >= len(self._guion):
            return False
        self._i += 1
        return True

    def isOpened(self):
        return True

    def release(self):
        self.liberada = True


class FrameSource:
    def __init__(self, abrir, max_reintentos=5, backoff_base=2.0, dormir=time.sleep,
                 es_archivo=False, loop=False, captura_inicial=None,
                 al_reconectar=None):
        self._abrir = abrir
        # None = no se rinde nunca. Es lo que hace una cámara colgada en una
        # pared: un corte de red de media tarde no puede costar el resto del día.
        self._max = max_reintentos
        self._base = backoff_base
        self._dormir = dormir
        self._al_reconectar = al_reconectar
        self.es_archivo = es_archivo
        self.loop = loop
        self._captura = captura_inicial
        self.reconexiones = 0
        self.cerrada = False
        self.fps_archivo = None
        self.ancho = None
        self.alto = None
        self.ultimo_error = ""
        if es_archivo and self._captura is not None:
            self._medir_captura()

    def leer(self, saltar=0):
        if self.cerrada:
            return None
        if self.es_archivo:
            return self._leer_archivo(saltar)
        return self._leer_red(saltar)

    def _leer_archivo(self, saltar=0):
        if self._captura is None:
            try:
                self._captura = self._abrir()
            except Exception:
                self._captura = None
            if self._captura is not None:
                self._medir_captura()

        if self._captura is None:
            self.cerrada = True
            return None

        for _ in range(saltar):
            self._captura.grab()

        ok, frame = self._captura.read()
        if ok:
            return frame

        # fin del archivo: rebobinar en bucle o cerrar
        if self.loop:
            self._rebobinar()
            ok, frame = self._captura.read()
            if ok:
                return frame

        self.cerrada = True
        self._soltar()
        return None

    def _leer_red(self, saltar=0):
        fallos = 0
        while True:
            if self._captura is None:
                try:
                    self._captura = self._abrir()
                    self.ultimo_error = ""
                except Exception as exc:
                    self._captura = None
                    self.ultimo_error = redactar(exc)

            if self._captura is not None:
                for _ in range(saltar):
                    self._captura.grab()
                ok, frame = self._captura.read()
                if ok:
                    return frame
                self.ultimo_error = "la fuente dejó de entregar imagen"
                self._soltar()

            fallos += 1
            if self._max is not None and fallos > self._max:
                break
            self.reconexiones += 1
            espera = min(self._base * (2 ** (fallos - 1)), BACKOFF_MAX)
            if self._al_reconectar is not None:
                self._al_reconectar(self.reconexiones, espera, self.ultimo_error)
            self._dormir(espera)

        self.cerrada = True
        return None

    def _medir_captura(self):
        try:
            self.fps_archivo = float(self._captura.get(cv2.CAP_PROP_FPS)) or None
            self.ancho = int(self._captura.get(cv2.CAP_PROP_FRAME_WIDTH)) or None
            self.alto = int(self._captura.get(cv2.CAP_PROP_FRAME_HEIGHT)) or None
        except Exception:
            pass

    def _rebobinar(self):
        try:
            self._captura.set(cv2.CAP_PROP_POS_FRAMES, 0)
        except Exception:
            pass

    def _soltar(self):
        if self._captura is not None:
            try:
                self._captura.release()
            except Exception:
                pass
            self._captura = None

    def cerrar(self):
        self._soltar()
        self.cerrada = True
