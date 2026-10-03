"""Alertas salientes. Webhook HTTPS es el canal primario porque la red de la
Javeriana bloquea SMTP; el email queda tras un flag para más adelante.

`ahora` y el backend se inyectan para probar anti-spam y fallos sin red ni reloj.
"""
from datetime import timedelta

from django.utils import timezone

from .horario import en_horario
from .models import AlertDelivery


class NullBackend:
    def __init__(self):
        self.enviados = []

    def enviar(self, destino, mensaje):
        self.enviados.append((destino, mensaje))


class WebhookBackend:
    def __init__(self, post=None):
        self._post = post or _post_https

    def enviar(self, destino, mensaje):
        self._post(destino, {"content": mensaje})


def _post_https(url, payload):
    import json
    import urllib.request

    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10).close()   # ponytail: stdlib, sin dep 'requests'


class EmailBackend:
    """Correo por el backend de Django, sin dependencias nuevas.

    En pruebas `EMAIL_BACKEND` es locmem (nada sale de la máquina), en
    desarrollo es console (el aviso se imprime y se lee), y en producción es el
    SMTP que Julián configure en `.env`.
    """

    ASUNTO = "Aviso de tu local"

    def enviar(self, destino, mensaje):
        from django.conf import settings
        from django.core.mail import send_mail

        send_mail(self.ASUNTO, mensaje,
                  getattr(settings, "DEFAULT_FROM_EMAIL", None),
                  [destino], fail_silently=False)


def backend_de(rule):
    """El canal que eligió el dueño manda; webhook sigue siendo el suelo."""
    return EmailBackend() if rule.canal == "email" else WebhookBackend()


class Notifier:
    def __init__(self, backend, ahora=timezone.now):
        self._backend = backend
        self._ahora = ahora

    def notificar(self, rule, mensaje):
        ahora = self._ahora()
        # Con el local cerrado no se despierta a nadie. Queda registrado para
        # que el dueño vea que hubo algo y que se decidió no avisarle: un aviso
        # perdido en silencio es peor que uno a deshora.
        if not en_horario(rule.business, ahora):
            return AlertDelivery.objects.create(rule=rule, mensaje=mensaje,
                                                resultado="fuera_hora")

        if rule.ultima_notificacion and \
                ahora - rule.ultima_notificacion < timedelta(minutes=rule.minutos_silencio):
            return AlertDelivery.objects.create(rule=rule, mensaje=mensaje, resultado="silenciada")

        try:
            self._backend.enviar(rule.destino, mensaje)
        except Exception as exc:
            return AlertDelivery.objects.create(rule=rule, mensaje=mensaje,
                                                resultado="fallo", error=str(exc)[:500])

        rule.ultima_notificacion = ahora
        rule.save(update_fields=["ultima_notificacion"])
        return AlertDelivery.objects.create(rule=rule, mensaje=mensaje, resultado="enviada")


def notificar_evento(event, notifier=None):
    reglas = AlertRule.objects.filter(business=event.camera.business,
                                      tipo_evento=event.kind, activa=True)
    msg = (f"[{event.camera.business.name}] {event.get_kind_display()} "
           f"en {event.zone_name}: {event.value}")
    for regla in reglas:
        # Un Notifier por regla: cada una puede ir por un canal distinto.
        (notifier or Notifier(backend_de(regla))).notificar(regla, msg)


from .models import AlertRule  # noqa: E402  (evita import circular arriba)
