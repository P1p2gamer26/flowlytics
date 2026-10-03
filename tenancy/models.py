import secrets
from datetime import time

from django.contrib.auth.models import User
from django.db import models

BUSINESS_KINDS = [
    ("cafe", "Cafetería"),
    ("restaurant", "Restaurante"),
    ("retail", "Tienda"),
    ("classroom", "Aula"),
    ("other", "Otro"),
]

ROLES = [
    ("owner", "Dueño"),
    ("admin", "Administrador"),
]


PLAN_POR_DEFECTO = {"max_camaras": 1, "retencion_dias": 90}


class Plan(models.Model):
    """Plan de servicio: límites de uso y un precio informativo.

    `precio_centavos` es la interfaz de cobro; no hay facturación real todavía.
    Cobrar es una decisión de negocio, no de código: se conecta un pago aquí
    cuando se decida."""
    nombre = models.CharField(max_length=50, unique=True)
    max_camaras = models.IntegerField(default=1)
    retencion_dias = models.IntegerField(default=90)
    precio_centavos = models.IntegerField(
        default=0, help_text="Interfaz de cobro; sin facturación real todavía.")

    def __str__(self):
        return self.nombre


class BusinessQuerySet(models.QuerySet):
    def for_user(self, user):
        profile = getattr(user, "profile", None)
        if profile is None:
            return self.none()
        if profile.role == "admin":
            return self
        if profile.business_id is None:
            return self.none()
        return self.filter(pk=profile.business_id)


class Business(models.Model):
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=20, choices=BUSINESS_KINDS, default="other")
    timezone = models.CharField(max_length=64, default="America/Bogota")
    abre = models.TimeField(
        default=time(0, 0),
        help_text="Hora a la que abre el local. Igual a la de cierre = avisar "
                  "a cualquier hora.",
    )
    cierra = models.TimeField(
        default=time(0, 0),
        help_text="Hora a la que cierra. Fuera de este rango no se manda "
                  "ningún aviso, aunque el evento sí se registre.",
    )
    comparte_corpus = models.BooleanField(
        default=True,
        help_text="Si está activo, las métricas anónimas de este negocio alimentan "
                  "el corpus comparativo. No afecta su capacidad de consultarlo.",
    )
    plan = models.ForeignKey(
        "Plan", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="businesses",
        help_text="Sin plan aplica el límite por defecto.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = BusinessQuerySet.as_manager()

    class Meta:
        verbose_name_plural = "businesses"

    def __str__(self):
        return self.name

    @property
    def max_camaras(self):
        return self.plan.max_camaras if self.plan_id else PLAN_POR_DEFECTO["max_camaras"]

    @property
    def retencion_dias(self):
        return self.plan.retencion_dias if self.plan_id else PLAN_POR_DEFECTO["retencion_dias"]

    def puede_agregar_camara(self):
        return self.cameras.count() < self.max_camaras


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLES, default="owner")
    # null para admins: no pertenecen a un negocio, los ven todos
    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, null=True, blank=True, related_name="members"
    )

    @property
    def is_admin(self):
        return self.role == "admin"

    def __str__(self):
        return f"{self.user.username} ({self.role})"


def _token_invitacion():
    return secrets.token_urlsafe(32)


class Invitation(models.Model):
    """Invitación a unirse a un negocio. El token es la credencial: quien lo tenga
    puede unirse a ESE negocio (y a ningún otro). No se manda correo desde la app;
    el enlace se comparte por fuera."""
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField(blank=True, default="")
    role = models.CharField(max_length=10, choices=ROLES, default="owner")
    token = models.CharField(max_length=64, unique=True, default=_token_invitacion)
    aceptada = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invitación a {self.business.name} ({self.email or 'sin email'})"


class AuditLog(models.Model):
    """Rastro de acciones sensibles. Sin borrado desde la aplicación."""
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField(max_length=50)
    objeto = models.CharField(max_length=200, blank=True, default="")
    ip = models.GenericIPAddressField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]

    @classmethod
    def registrar(cls, request, accion, objeto=""):
        user = getattr(request, "user", None)
        if not getattr(user, "is_authenticated", False):
            user = None
        ip = request.META.get("REMOTE_ADDR") if request is not None else None
        return cls.objects.create(usuario=user, accion=accion, objeto=str(objeto), ip=ip)

    def __str__(self):
        return f"{self.accion} por {self.usuario or 'anónimo'} @ {self.creado:%Y-%m-%d %H:%M}"


class IntentoLogin(models.Model):
    identificador = models.CharField(max_length=150)   # username intentado
    ip = models.GenericIPAddressField(null=True, blank=True)
    exito = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["identificador", "creado"])]

    @classmethod
    def fallidos_recientes(cls, identificador, ahora, ventana):
        return cls.objects.filter(identificador=identificador, exito=False,
                                  creado__gte=ahora - ventana).count()
