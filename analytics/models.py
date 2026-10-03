from datetime import datetime, timedelta, timezone as dt_timezone

from django.conf import settings
from django.db import models
from django.utils import timezone

from cameras.models import Camera
from tenancy.models import Business

EVENT_KINDS = [
    ("long_queue", "Fila larga"),
    ("empty_counter", "Caja desatendida"),
    ("overcrowding", "Aforo excedido"),
    ("crowded_queue", "Fila con mucha gente"),
]

ALERT_TIPOS = EVENT_KINDS + [("camara_caida", "Cámara sin señal")]
CANALES = [("webhook", "Webhook"), ("email", "Email")]


def _to_aware(epoch: float):
    return datetime.fromtimestamp(epoch, tz=dt_timezone.utc)


class MetricWindow(models.Model):
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name="windows")
    zone_name = models.CharField(max_length=80)
    zone_kind = models.CharField(max_length=20)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField()
    occupancy_avg = models.FloatField()
    occupancy_max = models.IntegerField()
    dwell_seconds = models.FloatField()
    unique_visitors = models.IntegerField()
    degradada = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["camera", "started_at"])]
        ordering = ["-started_at"]

    @classmethod
    def from_summary(cls, camera, summary, zone_kinds, degradada=False):
        rows = [
            cls(
                camera=camera,
                zone_name=name,
                zone_kind=zone_kinds.get(name, "general"),
                started_at=_to_aware(summary.started_at),
                ended_at=_to_aware(summary.ended_at),
                occupancy_avg=summary.occupancy_avg[name],
                occupancy_max=summary.occupancy_max[name],
                dwell_seconds=summary.dwell_seconds.get(name, 0.0),
                unique_visitors=summary.unique_visitors.get(name, 0),
                degradada=degradada,
            )
            for name in summary.occupancy_avg
        ]
        return cls.objects.bulk_create(rows)


class CrossingWindow(models.Model):
    """Entradas y salidas contadas por una línea en una ventana de tiempo.
    El aforo instantáneo vive en MetricWindow; esto es el flujo acumulado."""
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name="crossings")
    line_name = models.CharField(max_length=80)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField()
    entradas = models.IntegerField(default=0)
    salidas = models.IntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=["camera", "started_at"])]

    @classmethod
    def from_summary(cls, camera, summary):
        objs = [
            cls(camera=camera, line_name=name,
                started_at=_to_aware(summary.started_at),
                ended_at=_to_aware(summary.ended_at),
                entradas=entradas, salidas=salidas)
            for name, (entradas, salidas) in summary.crossings.items()
        ]
        return cls.objects.bulk_create(objs)

    def __str__(self):
        return f"{self.camera.name}/{self.line_name}: +{self.entradas} -{self.salidas}"


class Trajectory(models.Model):
    """Rastro ordenado de una persona a través del tiempo.

    Almacena los puntos de centro del bbox por frame para reconstruir el
    recorrido de izquierda a derecha sin guardar video completo. Un trajectory
    pertenece a una ventana de tiempo (MetricWindow) y a una cámara.
    """
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name="trajectories")
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField()
    track_id = models.IntegerField()
    # Puntos ordenados [x, y] del centro del bbox por frame, acumulados.
    points = models.JSONField(
        help_text="Lista ordenada de [x, y] centidesque pixel por frame. "
        "Permite reconstruir el rastro sin guardar video completo.")
    duration = models.FloatField(
        help_text="Duración en segundos: ended_at - started_at")

    class Meta:
        indexes = [models.Index(fields=["camera", "started_at"])]
        ordering = ["-started_at"]

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.points:
            raise ValidationError("Una trayectoria sin puntos no se guarda.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @classmethod
    def from_samples(cls, camera, samples, summary_ended_at):
        """Persiste una lista de `TrajectorySample` para una cámara. Los que
        tienen todos los puntos iguales (persona quieta) se ignoran.
        Devuelve la lista de `Trajectory` creados."""
        objs = []
        for s in samples:
            if not s.points:
                continue
            if all(p == s.points[0] for p in s.points):
                continue
            objs.append(cls(
                camera=camera,
                started_at=_to_aware(s.started_at),
                ended_at=_to_aware(s.ended_at),
                track_id=s.track_id,
                points=s.points,
                duration=s.ended_at - s.started_at,
            ))
        return cls.objects.bulk_create(objs)

    def __str__(self):
        return f"{self.camera.name} track {self.track_id} @ {self.started_at:%H:%M:%S}"


class Event(models.Model):
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name="events")
    kind = models.CharField(max_length=30, choices=EVENT_KINDS)
    zone_name = models.CharField(max_length=80)
    value = models.FloatField(help_text="Valor que disparó el evento (personas, segundos)")
    occurred_at = models.DateTimeField()

    class Meta:
        ordering = ["-occurred_at"]


class EventClip(models.Model):
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name="clip")
    file = models.FileField(upload_to="clips/%Y/%m/%d/")
    expires_at = models.DateTimeField()

    @staticmethod
    def default_expiry():
        return timezone.now() + timedelta(days=settings.CLIP_RETENTION_DAYS)

    @classmethod
    def purge_expired(cls):
        expired = cls.objects.filter(expires_at__lt=timezone.now())
        count = 0
        for clip in expired:
            clip.file.delete(save=False)
            clip.delete()
            count += 1
        return count


class JobRun(models.Model):
    """Última corrida de cada job periódico. Una fila por nombre (upsert)."""
    nombre = models.CharField(max_length=50, unique=True)
    terminado_en = models.DateTimeField(default=timezone.now)
    ok = models.BooleanField(default=True)
    detalle = models.TextField(blank=True, default="")

    @classmethod
    def marcar(cls, nombre, ok=True, detalle=""):
        obj, _ = cls.objects.update_or_create(
            nombre=nombre,
            defaults={"ok": ok, "detalle": detalle, "terminado_en": timezone.now()},
        )
        return obj

    @classmethod
    def ultima(cls, nombre):
        return cls.objects.filter(nombre=nombre).first()

    def __str__(self):
        return f"{self.nombre}: {'ok' if self.ok else 'fallo'} @ {self.terminado_en:%Y-%m-%d %H:%M}"


class AlertRule(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="alert_rules")
    tipo_evento = models.CharField(max_length=30, choices=ALERT_TIPOS)
    canal = models.CharField(max_length=10, choices=CANALES, default="webhook")
    destino = models.CharField(max_length=300, help_text="URL del webhook.")
    umbral = models.FloatField(
        null=True, blank=True,
        help_text="A partir de cuánto avisar, en la unidad del tipo de aviso "
                  "(segundos de espera, personas). Vacío = el del rubro.",
    )
    minutos_silencio = models.IntegerField(default=15)
    ultima_notificacion = models.DateTimeField(null=True, blank=True)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.business.name} / {self.get_tipo_evento_display()} -> {self.canal}"


class AlertDelivery(models.Model):
    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name="deliveries")
    mensaje = models.TextField()
    resultado = models.CharField(max_length=12)   # enviada | silenciada | fallo
    error = models.TextField(blank=True, default="")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]

class HeatmapWindow(models.Model):
    """Cuántas pisadas cayeron en cada celda de la rejilla, en una ventana de
    tiempo. Muchas filas por cámara, a propósito: a diferencia de
    `cameras.Recorrido` (un snapshot del último análisis, se sobrescribe),
    aquí cada ventana se conserva porque el mapa de calor necesita comparar
    un día contra otro, y `Recorrido` no tiene fecha para eso.
    """
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name="heatmaps")
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField()
    grid_rows = models.IntegerField()
    grid_cols = models.IntegerField()
    counts = models.JSONField(help_text="Matriz filas x columnas de pisadas por celda.")
    personas = models.IntegerField(
        default=0,
        help_text="Track ids distintos vistos en esta ventana. No dedupe entre "
        "ventanas: alguien que cruza el límite de una ventana a otra puede "
        "contarse dos veces. Aproximación aceptada, no un bug escondido.")

    class Meta:
        indexes = [models.Index(fields=["camera", "started_at"])]
        ordering = ["-started_at"]

    @classmethod
    def from_grid(cls, camera, started_epoch, ended_epoch, grid, personas):
        return cls.objects.create(
            camera=camera,
            started_at=_to_aware(started_epoch),
            ended_at=_to_aware(ended_epoch),
            grid_rows=len(grid),
            grid_cols=len(grid[0]) if grid else 0,
            counts=grid,
            personas=personas,
        )
