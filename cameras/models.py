import base64
import hashlib
from datetime import timedelta
from urllib.parse import urlparse, urlunparse

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from tenancy.models import Business

UMBRAL_LATIDO_SEG = 300

# Contexto de lo que se está mirando. Decide qué reglas de evento aplican
# (ver vision/core/events.py). Lo lleva la cámara; una zona puede sobrescribirlo
# cuando en un mismo frame conviven dos cosas distintas.
CONTEXTOS = [
    ("general", "General (aforo)"),
    ("queue", "Fila / espera"),
    ("counter", "Caja / mostrador"),
    ("staff", "Área de personal"),
    ("entrada", "Entrada / acceso"),
    ("pasillo", "Pasillo"),
    ("escaleras", "Escaleras eléctricas"),
    ("comidas", "Patio de comidas"),
    ("parqueadero", "Parqueadero"),
]


def clave_desde_secreto(secreto):
    """Clave Fernet derivada de un secreto (SECRET_KEY u otro, para rotación)."""
    digest = hashlib.sha256(secreto.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _clave_fernet():
    """Clave derivada de SECRET_KEY. Rotar SECRET_KEY sin antes correr
    `manage.py rotar_clave` invalida las credenciales guardadas."""
    return clave_desde_secreto(settings.SECRET_KEY)


def validate_polygon(value):
    if not isinstance(value, list) or len(value) < 3:
        raise ValidationError("Un polígono necesita al menos 3 puntos.")
    for point in value:
        if not (isinstance(point, list) and len(point) == 2):
            raise ValidationError("Cada punto debe ser [x, y].")
        if not all(isinstance(c, int) for c in point):
            raise ValidationError("Las coordenadas deben ser enteros (píxeles).")


def validate_line(value):
    if not isinstance(value, list) or len(value) != 2:
        raise ValidationError("Una línea de conteo necesita exactamente 2 puntos.")
    for point in value:
        if not (isinstance(point, list) and len(point) == 2):
            raise ValidationError("Cada punto debe ser [x, y].")
        if not all(isinstance(c, int) for c in point):
            raise ValidationError("Las coordenadas deben ser enteros (píxeles).")


def es_youtube(source):
    return any(h in urlparse(source).netloc for h in ("youtube.com", "youtu.be"))


def resolver_youtube(url):
    """OpenCV no abre una página de YouTube: yt-dlp da la URL HLS del video en
    vivo (480p: decodificar 720p a 30 fps ya satura la CPU de la VM). Esa URL caduca en ~6 h, por eso se resuelve en cada (re)conexión."""
    import yt_dlp

    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True,
                           "format": "bv*[height<=480]/b"}) as ydl:
        return ydl.extract_info(url, download=False)["url"]


class Camera(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="cameras")
    name = models.CharField(max_length=80)
    # "0" = webcam local; cualquier otra cosa se trata como URL (RTSP/HTTP)
    # o como archivo de video local si empieza con `file://` o existe en disco.
    source = models.CharField(max_length=300, default="0")
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    credencial_usuario = models.CharField(max_length=80, blank=True, default="")
    credencial_cifrada = models.BinaryField(blank=True, default=b"")
    # Resolución del frame de referencia sobre el que se dibujaron las zonas.
    # Si el stream llega con otra resolución, las zonas se escalan.
    frame_w = models.IntegerField(default=0)
    frame_h = models.IntegerField(default=0)
    # Calibración por cámara. Altura y ángulo se registran y se reportan; la zona
    # muerta (polígono en píxeles de referencia) sí filtra detecciones.
    altura_camara_m = models.FloatField(default=0)
    angulo_grados = models.FloatField(default=0)
    zona_muerta = models.JSONField(default=list, blank=True)
    lost_track_buffer = models.IntegerField(
        default=30, help_text="Frames que un track sobrevive a una oclusión.")
    contexto = models.CharField(
        max_length=20, choices=CONTEXTOS, blank=True, default="general",
        help_text="A qué apunta la cámara. Sus zonas lo heredan si no traen el suyo.")
    descripcion = models.CharField(
        max_length=300, blank=True, default="",
        help_text="Qué se ve en el video. La propone el asistente de IA y se puede corregir.")

    @property
    def es_video(self):
        from vision.core.source import es_fuente_archivo
        return es_fuente_archivo(self.source)

    def set_credencial(self, usuario, password):
        self.credencial_usuario = usuario
        self.credencial_cifrada = Fernet(_clave_fernet()).encrypt(password.encode())

    def _password(self):
        if not self.credencial_cifrada:
            return ""
        return Fernet(_clave_fernet()).decrypt(bytes(self.credencial_cifrada)).decode()

    def url_conexion(self):
        """URL completa con credenciales. Se construye en memoria y NUNCA se
        guarda ni se loguea."""
        if self.source.isdigit():
            return int(self.source)
        if es_youtube(self.source):
            return resolver_youtube(self.source)
        if not self.credencial_usuario:
            return self.source

        partes = urlparse(self.source)
        netloc = f"{self.credencial_usuario}:{self._password()}@{partes.netloc}"
        return urlunparse(partes._replace(netloc=netloc))

    @property
    def resolved_source(self):
        return self.url_conexion()

    def __str__(self):
        return f"{self.business.name} / {self.name}"


class Zone(models.Model):
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name="zones")
    name = models.CharField(max_length=80)
    kind = models.CharField(max_length=20, choices=CONTEXTOS, blank=True,
                            default="general",
                            help_text="Vacío = hereda el contexto de la cámara.")
    polygon = models.JSONField(validators=[validate_polygon])

    @property
    def contexto_efectivo(self):
        return self.kind or self.camera.contexto or "general"

    def __str__(self):
        return f"{self.camera.name} / {self.name} ({self.contexto_efectivo})"


class CountingLine(models.Model):
    """Línea de conteo de entrada/salida. Dos puntos en píxeles del frame de
    referencia (Camera.frame_w/frame_h). Un cruce en un sentido es entrada y en
    el otro salida; `invertir` los intercambia si el sentido quedó al revés."""
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name="lines")
    name = models.CharField(max_length=80)
    puntos = models.JSONField(validators=[validate_line])
    invertir = models.BooleanField(default=False,
                                   help_text="Intercambia entrada y salida.")

    def __str__(self):
        return f"{self.camera.name} / línea {self.name}"


class CameraHealthQuerySet(models.QuerySet):
    def caidas(self, business, umbral_segundos=UMBRAL_LATIDO_SEG):
        limite = timezone.now() - timedelta(seconds=umbral_segundos)
        return self.filter(camera__business=business, ultimo_latido__lt=limite)


class CameraHealth(models.Model):
    camera = models.OneToOneField(Camera, on_delete=models.CASCADE,
                                  related_name="salud")
    ultimo_latido = models.DateTimeField(default=timezone.now)
    frames_leidos = models.IntegerField(default=0)
    reconexiones = models.IntegerField(default=0)
    ultimo_error = models.TextField(blank=True, default="")
    fps_medido = models.FloatField(default=0.0)
    frames_descartados = models.IntegerField(default=0)

    objects = CameraHealthQuerySet.as_manager()

    @classmethod
    def latir(cls, camera, frames, reconexiones, error="", fps_medido=0.0, frames_descartados=0):
        salud, _ = cls.objects.update_or_create(
            camera=camera,
            defaults={"frames_leidos": frames, "reconexiones": reconexiones,
                      "ultimo_error": error, "ultimo_latido": timezone.now(),
                      "fps_medido": fps_medido, "frames_descartados": frames_descartados},
        )
        return salud

    def esta_viva(self, umbral_segundos=UMBRAL_LATIDO_SEG):
        return (timezone.now() - self.ultimo_latido).total_seconds() < umbral_segundos

    def __str__(self):
        return f"{self.camera.name}: {'viva' if self.esta_viva() else 'caida'}"


class Recorrido(models.Model):
    """Lo que el detector vio, instante a instante, en el último análisis.

    Una fila por cámara con todo el recorrido dentro, en vez de una fila por caja:
    dos minutos a 2 FPS con ocho personas son ~2000 cajas, y el front las quiere
    TODAS de golpe para poder pintarlas mientras el video corre. Una consulta y un
    JSON pesan menos que dos mil filas y un ORDER BY.
    """

    camera = models.OneToOneField(Camera, on_delete=models.CASCADE,
                                  related_name="recorrido")
    pistas = models.JSONField(default=list)
    actualizado = models.DateTimeField(auto_now=True)

    def permanencias(self):
        """{track_id: segundos} de la primera a la última vez que se le vio."""
        visto = {}
        for instante in self.pistas:
            for caja in instante.get("cajas", []):
                ini = visto.get(caja["id"], (instante["t"], instante["t"]))[0]
                visto[caja["id"]] = (ini, instante["t"])
        return {tid: round(fin - ini, 1) for tid, (ini, fin) in visto.items()}


class MarcaPersona(models.Model):
    """Este rastro de ESTA corrida es un empleado. Lo dice el dueño, no el modelo.

    Es una etiqueta sobre un `track_id`, que solo existe dentro del análisis que lo
    generó: al reanalizar el video los ids cambian y estas marcas dejan de aplicar.
    La limitación es deliberada — recordar a una persona entre corridas sería
    re-identificación biométrica, que el README promete no hacer.
    """

    camera = models.ForeignKey(Camera, on_delete=models.CASCADE,
                               related_name="marcas_persona")
    track_id = models.IntegerField()
    es_personal = models.BooleanField(default=True)

    class Meta:
        unique_together = ("camera", "track_id")
