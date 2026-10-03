def retomar_analisis(camera_id):
    from vision.models import Recorrido
    return Recorrido.objects.filter(
        camera_id=camera_id, pistas__isnull=False
    ).last()


def obtener_fuente(video):
    from vision.core.fuente_video import FuenteVideo
    from vision.core.archivo_video import ArchivoVideo
    if video.startswith("rtsp://"):
        fuente = FuenteVideo(url=video)
    else:
        fuente = ArchivoVideo(path=video)
    return fuente
