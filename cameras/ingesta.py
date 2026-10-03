"""De "un video que me diste" a un mp4 en disco que el navegador reproduce.

Tres realidades distintas entran por aquí: un archivo que sube el navegador,
un enlace directo a un mp4, y una página de YouTube o Vimeo. Salen todas como
la misma cosa: una ruta a un H.264 dentro de MEDIA_ROOT/subidas.
"""
import re
import uuid
from pathlib import Path

import cv2
from django.conf import settings

from vision.core.codecs import es_h264

CARPETA = "subidas"
# ponytail: 500 MB, suficiente para un clip de demo de varios minutos.
# Si hace falta más, sube esto antes de inventar carga por trozos.
MAX_BYTES = 500 * 1024 * 1024


def _carpeta():
    ruta = Path(settings.MEDIA_ROOT) / CARPETA
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def destino_para(nombre):
    """Ruta libre dentro de subidas/. El nombre que llega es del usuario:
    se queda solo con el tallo alfanumérico, así un '../..' no escapa."""
    tallo = re.sub(r"[^A-Za-z0-9_-]", "_", Path(nombre).stem)[:60] or "video"
    carpeta = _carpeta()
    ruta = carpeta / f"{tallo}.mp4"
    if ruta.exists():
        ruta = carpeta / f"{tallo}-{uuid.uuid4().hex[:8]}.mp4"
    return ruta


def guardar_subida(archivo, nombre):
    if archivo.size > MAX_BYTES:
        raise ValueError(f"El archivo pesa más de {MAX_BYTES // (1024 * 1024)} MB.")
    ruta = destino_para(nombre)
    with open(ruta, "wb") as salida:
        for trozo in archivo.chunks():
            salida.write(trozo)
    return ruta


def _descargar_con_ytdlp(url, plantilla_salida):
    import yt_dlp

    opciones = {
        "outtmpl": str(plantilla_salida),
        # mp4 ya multiplexado: sin esto yt-dlp baja video y audio por separado
        # y necesita ffmpeg para unirlos.
        "format": "best[ext=mp4]/best",
        "quiet": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opciones) as ydl:
        info = ydl.extract_info(url, download=True)
        return Path(ydl.prepare_filename(info))


def descargar_url(url, descargador=None):
    """Baja el video de `url`. `descargador` se inyecta en los tests para no
    tocar la red."""
    if not url.startswith(("http://", "https://")):
        raise ValueError("La URL debe empezar por http:// o https://")
    descargador = descargador or _descargar_con_ytdlp
    plantilla = _carpeta() / f"{uuid.uuid4().hex[:8]}.%(ext)s"
    return Path(descargador(url, plantilla))


def asegurar_h264(ruta):
    """Devuelve una ruta a H.264. Si el archivo no lo es, lo reconvierte;
    si tampoco se puede leer, avisa en vez de dejar un video negro."""
    ruta = Path(ruta)
    if es_h264(ruta):
        return ruta

    tmp = ruta.with_suffix(".tmp.mp4")
    cap = cv2.VideoCapture(str(ruta))
    escritor = None
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if escritor is None:
                alto, ancho = frame.shape[:2]
                escritor = cv2.VideoWriter(
                    str(tmp), cv2.VideoWriter_fourcc(*"avc1"), fps, (ancho, alto))
            escritor.write(frame)
    finally:
        cap.release()
        if escritor is not None:
            escritor.release()

    if escritor is None or not es_h264(tmp):
        tmp.unlink(missing_ok=True)
        raise ValueError("No se pudo convertir el video a H.264. "
                         "Prueba con otro archivo o con un mp4.")
    tmp.replace(ruta)
    return ruta
