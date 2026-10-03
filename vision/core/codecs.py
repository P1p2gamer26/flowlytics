"""Saber si un mp4 lo puede reproducir un navegador.

OpenCV lee mp4v (MPEG-4 Part 2) sin problema, así que un archivo roto para la
web pasa desapercibido en el worker y solo se nota como un video en negro.
"""
from pathlib import Path


def es_h264(ruta):
    """True si el contenedor declara avc1 (H.264), el único de los que escribe
    OpenCV que reproducen todos los navegadores."""
    ruta = Path(ruta)
    if not ruta.is_file():
        return False
    # El atom con el códec puede estar al final: hay que mirar el archivo entero.
    return b"avc1" in ruta.read_bytes()
