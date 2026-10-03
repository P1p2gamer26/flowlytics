import base64
import json
import os
import time
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import cv2
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from tenancy.models import AuditLog
from tenancy.permissions import business_or_403
from tenancy.rubros import perfil
from vision.core.rastros import rastros_de_pistas
from vision.core.source import es_fuente_archivo, ruta_archivo

from analytics.models import Trajectory

from .diagnostico import diagnosticar
from .models import Camera, CountingLine, MarcaPersona, Recorrido, Zone
from .serializers import CameraSerializer, LineaSerializer, ZoneSerializer


def _en_vivo(camera_id, max_edad=30):
    """Personas que el worker vio hace menos de `max_edad` s (en_vivo/<id>.json),
    o None si no hay dato fresco."""
    ruta = os.path.join(settings.MEDIA_ROOT, "en_vivo", f"{camera_id}.json")
    try:
        with open(ruta) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data.get("personas", 0) if time.time() - data.get("t", 0) < max_edad else None


def _sondear_tcp(host, puerto, timeout=3.0):
    """¿Hay algo escuchando ahí? Distingue 'apagada' de 'contraseña mala'."""
    import socket
    try:
        with socket.create_connection((host, puerto), timeout=timeout):
            return True
    except OSError:
        return False


def _abrir_stream(url, timeout_ms=5000):
    """VideoCapture con tope de espera: sin él, una IP muerta cuelga la petición."""
    try:
        return cv2.VideoCapture(url, cv2.CAP_FFMPEG,
                                [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_ms,
                                 cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_ms])
    except (AttributeError, TypeError):
        return cv2.VideoCapture(url)


def _camara_o_403(user, camera_id):
    camera = Camera.objects.filter(pk=camera_id).first()
    if camera is None:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("No existe o no tienes acceso.")
    business_or_403(user, camera.business_id)
    return camera


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def camaras_view(request):
    if request.method == "GET":
        business = business_or_403(request.user, request.query_params.get("business"))
        camaras = Camera.objects.filter(business=business).prefetch_related("zones")
        return Response(CameraSerializer(camaras, many=True).data)

    business = business_or_403(request.user, request.data.get("business"))
    if not business.puede_agregar_camara():
        return Response(
            {"error": f"Tu plan permite hasta {business.max_camaras} cámara(s). "
                      "Actualiza el plan para agregar más."},
            status=status.HTTP_402_PAYMENT_REQUIRED,
        )
    serializer = CameraSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(business=business)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def camaras_grid_view(request):
    """Lo que hace falta para pintar una celda de la pared de cámaras: nombre,
    si sigue mandando señal, y cuánta gente había en el último análisis.

    Junta CameraHealth (Fase 4) y Recorrido (recorridos) en dos consultas,
    no una por cámara: nueve cámaras en un grid no pueden costar nueve
    conexiones de video (eso es lo que hace /vista/, y por eso el grid no la
    usa) ni nueve peticiones del recorrido completo (eso hace /recorrido/,
    y el grid solo necesita el último instante, no la película entera).
    """
    business = business_or_403(request.user, request.query_params.get("business"))
    camaras = Camera.objects.filter(business=business).select_related("salud")

    recorridos = {
        r.camera_id: r.pistas[-1] if r.pistas else None
        for r in Recorrido.objects.filter(camera__business=business)
    }

    filas = []
    for camara in camaras:
        instante = recorridos.get(camara.pk)
        salud = getattr(camara, "salud", None)
        viva = salud.esta_viva() if salud else False
        gente_ahora = len(instante["cajas"]) if instante else 0

        fresco = _en_vivo(camara.pk)
        if fresco is not None:
            gente_ahora, viva = fresco, True

        filas.append({
            "id": camara.pk,
            "name": camara.name,
            "es_video": camara.es_video,
            "viva": viva,
            "analizado": instante is not None,
            "gente_ahora": gente_ahora,
            "ultimo_error": salud.ultimo_error if salud else "",
        })
    return Response(filas)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def camara_detalle_view(request, camera_id):
    camera = _camara_o_403(request.user, camera_id)

    if request.method == "GET":
        # El rubro va solo en el detalle: el editor de zonas lo necesita y el
        # listado no, y es el mismo para todas las cámaras del negocio.
        return Response({**CameraSerializer(camera).data,
                         "rubro": perfil(camera.business.kind)})
    if request.method == "DELETE":
        camera.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = CameraSerializer(camera, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def camara_ahora_view(request, camera_id):
    """Devuelve el frame anotado más reciente como JPEG.
    Si no existe el archivo en MEDIA_ROOT/en_vivo/<camera_id>.jpg, devuelve 404.
    Cache-Control: no-store para que no se cachee."""
    camera = _camara_o_403(request.user, camera_id)

    jpg_path = os.path.join(settings.MEDIA_ROOT, "en_vivo", f"{camera_id}.jpg")
    if not os.path.isfile(jpg_path):
        return Response({"error": "No hay imagen en vivo disponible."}, status=status.HTTP_404_NOT_FOUND)

    # Se lee entero y se suelta: con FileResponse el archivo queda abierto y en
    # Windows el worker no puede reemplazarlo (os.replace da PermissionError).
    with open(jpg_path, "rb") as f:
        response = HttpResponse(f.read(), content_type="image/jpeg")
    response["Cache-Control"] = "no-store"
    return response


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def zonas_view(request, camera_id):
    camera = _camara_o_403(request.user, camera_id)

    if request.method == "GET":
        return Response(ZoneSerializer(camera.zones.all(), many=True).data)

    serializer = ZoneSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(camera=camera)
    AuditLog.registrar(request, "crear_zona", objeto=f"Zone#{serializer.instance.pk}")
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def lineas_view(request, camera_id):
    camera = _camara_o_403(request.user, camera_id)

    if request.method == "GET":
        return Response(LineaSerializer(camera.lines.all(), many=True).data)

    serializer = LineaSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(camera=camera)
    AuditLog.registrar(request, "crear_linea",
                       objeto=f"CountingLine#{serializer.instance.pk}")
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def linea_detalle_view(request, linea_id):
    linea = CountingLine.objects.filter(pk=linea_id).select_related("camera").first()
    if linea is None:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("No existe o no tienes acceso.")
    business_or_403(request.user, linea.camera.business_id)

    if request.method == "DELETE":
        linea.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = LineaSerializer(linea, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    AuditLog.registrar(request, "cambiar_linea", objeto=f"CountingLine#{linea.pk}")
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def camara_vista_view(request, camera_id):
    """Primer frame de la cámara como JPEG, para dibujar zonas y líneas sobre la
    imagen real. Un archivo se abre por su ruta; una cámara en vivo, con sus
    credenciales y con tope de espera. Una conexión, un frame, y se suelta."""
    camera = _camara_o_403(request.user, camera_id)

    es_archivo = es_fuente_archivo(camera.source)
    if es_archivo:
        cap = cv2.VideoCapture(ruta_archivo(camera.source))
    elif camera.source == "0":
        cap = cv2.VideoCapture(0)
    else:
        cap = _abrir_stream(camera.url_conexion())

    ok, frame = False, None
    try:
        ok, frame = cap.read()
        if ok:
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or frame.shape[1]
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or frame.shape[0]
    finally:
        cap.release()

    if not ok:
        if es_archivo or camera.source == "0":
            return Response({"error": "No se pudo leer un frame de la fuente."},
                            status=status.HTTP_400_BAD_REQUEST)
        motivo = diagnosticar(camera.source, _sondear_tcp,
                              lambda: _abrir_stream(camera.url_conexion()))["mensaje"]
        return Response({"error": motivo}, status=status.HTTP_400_BAD_REQUEST)

    camera.frame_w, camera.frame_h = w, h
    camera.save(update_fields=["frame_w", "frame_h"])

    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        return Response({"error": "No se pudo codificar el frame."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    b64 = base64.b64encode(buf.tobytes()).decode()
    return Response({
        "width": w, "height": h, "image": f"data:image/jpeg;base64,{b64}",
        "video": (f"/api/camaras/{camera_id}/video/"
                  if es_archivo else None),
    })


def _ruta_de_video_permitida(camera):
    """Ruta real del video si la cámara es de archivo y cae dentro de
    VIDEO_ROOTS. None si no es de archivo; PermissionDenied si se sale."""
    from pathlib import Path

    from django.conf import settings
    from django.core.exceptions import PermissionDenied

    if not es_fuente_archivo(camera.source):
        return None

    ruta = Path(ruta_archivo(camera.source)).resolve()
    permitidas = [Path(r).resolve() for r in settings.VIDEO_ROOTS]
    if not any(ruta == raiz or raiz in ruta.parents for raiz in permitidas):
        raise PermissionDenied("El archivo está fuera de las carpetas permitidas.")
    return ruta


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def camara_video_view(request, camera_id):
    """Sirve el archivo de video para que el editor dibuje sobre imagen en
    movimiento. Solo cámaras de archivo: un RTSP no tiene archivo que servir."""
    from django.http import FileResponse

    camera = _camara_o_403(request.user, camera_id)
    ruta = _ruta_de_video_permitida(camera)
    if ruta is None:
        return Response({"error": "Solo las cámaras de archivo tienen video."},
                        status=status.HTTP_400_BAD_REQUEST)
    if not ruta.is_file():
        return Response({"error": "El archivo no existe."},
                        status=status.HTTP_404_NOT_FOUND)
    return FileResponse(ruta.open("rb"), content_type="video/mp4")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def camara_sugerir_zona_view(request, camera_id):
    """Propone un polígono con el recorrido de la gente en los primeros
    segundos de video. Sugiere geometría; el nombre y el tipo los pone quien
    dibuja."""
    from django.conf import settings as cfg

    from vision.core.detector import YoloDetector
    from vision.core.muestreo import MUESTRAS_MAXIMAS
    from vision.core.sugerencia import (MUESTRAS_MINIMAS, poligono_sugerido,
                                        recorrido_de_video)

    camera = _camara_o_403(request.user, camera_id)
    ruta = _ruta_de_video_permitida(camera)
    entrada = str(ruta) if ruta is not None else (0 if camera.source == "0" else None)
    if entrada is None:
        return Response({"error": "Solo se puede sugerir sobre archivos de video o webcam."},
                        status=status.HTTP_400_BAD_REQUEST)

    from django.core.cache import cache

    segundos = float(request.query_params.get("segundos", 60))
    # El mtime en la clave: si cambia el archivo, la sugerencia caduca sola.
    sello = ruta.stat().st_mtime_ns if ruta is not None else 0
    clave = f"sugerencia:{camera.pk}:{sello}:{segundos:g}"
    if request.query_params.get("refrescar") != "1":
        guardado = cache.get(clave)
        if guardado is not None:
            return Response({**guardado, "cacheado": True})

    detector = YoloDetector(cfg.DETECTOR_MODEL, cfg.DETECTOR_IMGSZ, cfg.DETECTOR_DEVICE)

    def analizar(maximo):
        """Detecciones de pies y tamaño del frame, con un presupuesto de muestras."""
        return recorrido_de_video(entrada, detector, segundos, cfg.SAMPLE_FPS, maximo)

    # Primero barato. Si el video tiene poca gente y no alcanza el mínimo, se
    # insiste con todas las muestras: el coste alto se paga solo cuando sirve.
    recorrido, w, h = analizar(MUESTRAS_MAXIMAS)
    poly = poligono_sugerido(recorrido, (w, h))
    if poly is None:
        recorrido, w, h = analizar(None)
        poly = poligono_sugerido(recorrido, (w, h))
    if poly is None:
        return Response(
            {"error": f"Solo {len(recorrido)} detecciones en {segundos:g} s: no alcanza "
                      f"para sugerir una zona (hacen falta {MUESTRAS_MINIMAS}). "
                      "Prueba con más segundos o con un video con más gente.",
             "recorrido": recorrido},
            status=status.HTTP_400_BAD_REQUEST)
    # El recorrido va aparte del polígono: muestra de dónde salió la sugerencia.
    payload = {"polygon": poly, "recorrido": recorrido,
               "muestras": len(recorrido), "width": w, "height": h}
    # Los errores no se cachean a propósito: si cambias el video o el umbral,
    # quieres que reintente.
    cache.set(clave, payload, 60 * 60)
    return Response({**payload, "cacheado": False})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def subir_video_view(request):
    """Recibe un archivo o una URL y deja una cámara lista para analizar."""
    from cameras.ingesta import asegurar_h264, descargar_url, guardar_subida

    business = business_or_403(request.user, request.data.get("business"))
    if not business.puede_agregar_camara():
        return Response(
            {"error": f"Tu plan permite hasta {business.max_camaras} cámara(s)."},
            status=status.HTTP_402_PAYMENT_REQUIRED)

    archivo = request.FILES.get("archivo")
    url = (request.data.get("url") or "").strip()
    if archivo is None and not url:
        return Response({"error": "Sube un archivo o pega una URL de video."},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        ruta = guardar_subida(archivo, archivo.name) if archivo else descargar_url(url)
        ruta = asegurar_h264(ruta)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        return Response({"error": "No se pudo traer el video de esa URL."},
                        status=status.HTTP_400_BAD_REQUEST)

    camera = Camera.objects.create(
        business=business,
        name=request.data.get("name") or ruta.stem,
        source=str(ruta),
    )
    AuditLog.registrar(request, "subir_video", objeto=f"Camera#{camera.pk}")
    return Response(CameraSerializer(camera).data, status=status.HTTP_201_CREATED)


@api_view(["PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def zona_detalle_view(request, zona_id):
    zona = Zone.objects.filter(pk=zona_id).select_related("camera").first()
    if zona is None:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("No existe o no tienes acceso.")
    business_or_403(request.user, zona.camera.business_id)

    if request.method == "DELETE":
        zona.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = ZoneSerializer(zona, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    AuditLog.registrar(request, "cambiar_zona", objeto=f"Zone#{zona.pk}")
    return Response(serializer.data)


def _cliente_llm():
    from insights.client import LlmClient
    return LlmClient()


def _primer_frame_jpeg(camera):
    """El primer frame legible, ya en JPEG. None si la fuente no da imagen."""
    ruta = _ruta_de_video_permitida(camera)
    entrada = str(ruta) if ruta is not None else (0 if camera.source == "0" else None)
    if entrada is None:
        return None
    cap = cv2.VideoCapture(entrada)
    try:
        ok, frame = cap.read()
    finally:
        cap.release()
    if not ok:
        return None
    ok, buf = cv2.imencode(".jpg", frame)
    return buf.tobytes() if ok else None


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def camara_describir_view(request, camera_id):
    """Mira un frame y escribe qué se ve. La frase queda editable: esto
    propone, no decide."""
    from django.conf import settings as cfg

    from insights.escena import describir_frame

    camera = _camara_o_403(request.user, camera_id)
    if not cfg.ANTHROPIC_API_KEY:
        return Response(
            {"error": "No hay clave del asistente de IA configurada: escribe la descripción a mano."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE)

    jpeg = _primer_frame_jpeg(camera)
    if jpeg is None:
        return Response({"error": "No se pudo leer un frame del video."},
                        status=status.HTTP_400_BAD_REQUEST)

    datos = describir_frame(jpeg, _cliente_llm())
    camera.descripcion = datos["descripcion"]
    camera.contexto = datos["contexto"]
    camera.save(update_fields=["descripcion", "contexto"])
    return Response(datos)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def camara_procesar_view(request, camera_id):
    from cameras.procesamiento import lanzar

    camera = _camara_o_403(request.user, camera_id)
    try:
        lanzar(camera, segundos=request.data.get("segundos"))
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    AuditLog.registrar(request, "procesar_video", objeto=f"Camera#{camera.pk}")
    return Response({"lanzado": True}, status=status.HTTP_202_ACCEPTED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def camara_progreso_view(request, camera_id):
    from cameras.procesamiento import progreso

    return Response(progreso(_camara_o_403(request.user, camera_id)))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def camara_trayectorias_view(request, camera_id):
    """Recorridos guardados para la cámara: cada uno con su `track_id` y la
    lista de puntos ordenada por frame, para que el editor los dibuje.
    Con ?minutos=N filtra a los últimos N minutos (máx. 300 trayectorias)."""
    camera = _camara_o_403(request.user, camera_id)

    qs = camera.trajectories.all()
    minutos = request.query_params.get("minutos")
    if minutos is not None:
        try:
            m = int(minutos)
            if m > 0:
                desde = timezone.now() - timedelta(minutes=m)
                qs = qs.filter(started_at__gte=desde)
        except ValueError:
            pass

    recorridos = [
        {"track_id": t.track_id, "points": t.points,
         "started_at": t.started_at.isoformat()}
        for t in qs.order_by("-started_at")[:300]
    ]
    return Response({"recorridos": recorridos})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def probar_camara_view(request):
    """Prueba una dirección ANTES de guardarla: quien cuelga una cámara se
    equivoca de URL tres veces antes de acertar, y cada intento no puede costar
    una cámara creada y borrada."""
    business_or_403(request.user, request.data.get("business"))
    source = (request.data.get("source") or "").strip()
    usuario = (request.data.get("usuario") or "").strip()

    sonda = Camera(source=source)
    if usuario:
        sonda.set_credencial(usuario, request.data.get("password") or "")
    url = sonda.url_conexion()

    return Response(diagnosticar(source, _sondear_tcp, lambda: _abrir_stream(url)))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def camara_recorrido_view(request, camera_id):
    """Dónde estuvo cada persona, para dibujarlo encima del video.

    Va todo de una vez y no por trozos: el front necesita poder pintar cualquier
    instante en cuanto el usuario mueve la barra del video, y pedir por rango
    convertiría cada salto en una espera. Un video de dos minutos son ~200 KB.
    """
    camera = _camara_o_403(request.user, camera_id)
    recorrido = Recorrido.objects.filter(camera=camera).first()
    personal = list(
        MarcaPersona.objects.filter(camera=camera, es_personal=True)
        .order_by("track_id").values_list("track_id", flat=True))

    if recorrido is None:
        # Sin análisis todavía no es un error: es una cámara que nadie ha mirado.
        return Response({"pistas": [], "rastros": [], "permanencias": {},
                         "personal": personal, "analizado": False})

    return Response({
        "pistas": recorrido.pistas,
        "rastros": rastros_de_pistas(recorrido.pistas),
        # Las claves de un JSON son texto; el front las vuelve a mirar como texto.
        "permanencias": {str(k): v for k, v in recorrido.permanencias().items()},
        "personal": personal,
        "analizado": True,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def camara_mapa_calor_view(request, camera_id):
    """Dónde se para la gente en un periodo: la rejilla ya suavizada y
    normalizada, lista para pintar. Los últimos 7 días si no se pide rango,
    igual que el reporte CSV/PDF."""
    from datetime import date, timedelta

    from analytics.mapa_calor import mapa_calor_periodo

    camera = _camara_o_403(request.user, camera_id)

    hasta = request.query_params.get("hasta")
    desde = request.query_params.get("desde")
    franja = request.query_params.get("franja") or None
    try:
        hasta = date.fromisoformat(hasta) if hasta else date.today()
        desde = date.fromisoformat(desde) if desde else hasta - timedelta(days=6)
    except ValueError:
        return Response({"error": "Fecha inválida, use YYYY-MM-DD"},
                        status=status.HTTP_400_BAD_REQUEST)
    if desde > hasta:
        return Response({"error": "El rango está al revés."},
                        status=status.HTTP_400_BAD_REQUEST)
    if franja not in (None, "manana", "tarde"):
        return Response({"error": "franja debe ser 'manana' o 'tarde'."},
                        status=status.HTTP_400_BAD_REQUEST)

    r = mapa_calor_periodo(camera, desde, hasta, franja=franja)
    return Response({
        "grid": r["grid"], "personas": r["personas"], "mensaje": r["mensaje"],
        "cols": len(r["grid"][0]) if r["grid"] else 0,
        "rows": len(r["grid"]) if r["grid"] else 0,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def camaras_en_vivo_view(request):
    """Todas las cámaras de los negocios visibles para el usuario, con la info
    necesaria para pintarlas en vivo: tipo de fuente, youtube_id, video URL,
    dimensiones, estado (viva/gente_ahora) y zonas. No abre streams."""
    from tenancy.models import Business
    from .models import es_youtube

    negocios = Business.objects.for_user(request.user)
    camaras = Camera.objects.filter(business__in=negocios, enabled=True).select_related("salud", "business").prefetch_related("zones")

    # Recorridos del último análisis por cámara (para gente_ahora)
    recorridos = {
        r.camera_id: r.pistas[-1] if r.pistas else None
        for r in Recorrido.objects.filter(camera__in=camaras)
    }

    filas = []
    for camara in camaras:
        if camara.es_video:
            tipo = "archivo"
            youtube_id = None
        elif es_youtube(camara.source):
            tipo = "youtube"
            u = urlparse(camara.source)
            if u.netloc.endswith("youtu.be"):
                youtube_id = u.path.lstrip("/")
            else:
                youtube_id = parse_qs(u.query).get("v", [None])[0]
        else:
            tipo = "stream"
            youtube_id = None

        # video URL (solo archivos)
        video = f"/api/camaras/{camara.pk}/video/" if camara.es_video else None

        # width/height: si son 0 y es archivo, leer UNA vez con cv2 y guardar
        w, h = camara.frame_w, camara.frame_h
        if w == 0 or h == 0:
            if camara.es_video:
                ruta = _ruta_de_video_permitida(camara)
                if ruta and ruta.is_file():
                    cap = cv2.VideoCapture(str(ruta))
                    try:
                        if cap.isOpened():
                            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 0
                            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 0
                    finally:
                        cap.release()
                    if w and h:
                        camara.frame_w, camara.frame_h = w, h
                        camara.save(update_fields=["frame_w", "frame_h"])

        # viva/gente_ahora (misma lógica que camaras_grid_view)
        instante = recorridos.get(camara.pk)
        salud = getattr(camara, "salud", None)
        viva = salud.esta_viva() if salud else False
        gente_ahora = len(instante["cajas"]) if instante else 0

        fresco = _en_vivo(camara.pk)
        if fresco is not None:
            gente_ahora, viva = fresco, True

        # zonas
        zonas = [
            {"id": z.id, "name": z.name, "kind": z.kind, "polygon": z.polygon}
            for z in camara.zones.all()
        ]

        filas.append({
            "id": camara.pk,
            "name": camara.name,
            "negocio": camara.business.name,
            "negocio_id": camara.business_id,
            "tipo": tipo,
            "youtube_id": youtube_id,
            "video": video,
            "width": w,
            "height": h,
            "viva": viva,
            "gente_ahora": gente_ahora,
            "zonas": zonas,
        })

    return Response(filas)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def camara_personal_view(request, camera_id):
    """Marca (o desmarca) un rastro como empleado. Lo decide el dueño, no el modelo."""
    camera = _camara_o_403(request.user, camera_id)
    try:
        track_id = int(request.data.get("track_id"))
    except (TypeError, ValueError):
        return Response({"error": "Falta el track_id de la persona."},
                        status=status.HTTP_400_BAD_REQUEST)

    es_personal = bool(request.data.get("es_personal", True))
    MarcaPersona.objects.update_or_create(
        camera=camera, track_id=track_id, defaults={"es_personal": es_personal})

    personal = list(
        MarcaPersona.objects.filter(camera=camera, es_personal=True)
        .order_by("track_id").values_list("track_id", flat=True))
    return Response({"personal": personal})
