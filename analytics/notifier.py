"""Alertas salientes. Webhook HTTPS es el canal primario porque la red de la
Javeriana bloquea SMTP; el email queda tras un flag para más adelante.

`ahora` y el backend se inyectan para probar anti-spam y fallos sin red ni reloj.
"""
from datetime import timedelta

from django.utils import timezone

from .horario import en_horario
from .models import AlertDelivery, AlertRule


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
    urllib.request.urlopen(req, timeout=10).close()


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


class RegistroBackend:
    """Backend que no envía nada: la AlertDelivery es el registro."""

    def enviar(self, destino, mensaje):
        pass


def backend_de(rule):
    """El canal que eligió el dueño manda; webhook sigue siendo el suelo.
    Para acciones operativas (distintas de 'avisar') se usa RegistroBackend.
    """
    if rule.accion != "avisar":
        return RegistroBackend()
    return EmailBackend() if rule.canal == "email" else WebhookBackend()


class Notifier:
    def __init__(self, backend, ahora=timezone.now):
        self._backend = backend
        self._ahora = ahora

    def notificar(self, rule, mensaje, camara="", simulado=False):
        ahora = self._ahora()
        if not en_horario(rule.business, ahora):
            return AlertDelivery.objects.create(
                rule=rule, mensaje=mensaje, resultado="fuera_hora",
                camara=camara, simulado=simulado
            )

        if rule.ultima_notificacion and \
                ahora - rule.ultima_notificacion < timedelta(minutes=rule.minutos_silencio):
            return AlertDelivery.objects.create(
                rule=rule, mensaje=mensaje, resultado="silenciada",
                camara=camara, simulado=simulado
            )

        try:
            self._backend.enviar(rule.destino, mensaje)
        except Exception as exc:
            return AlertDelivery.objects.create(
                rule=rule, mensaje=mensaje, resultado="fallo",
                error=str(exc)[:500], camara=camara, simulado=simulado
            )

        rule.ultima_notificacion = ahora
        rule.save(update_fields=["ultima_notificacion"])
        resultado = "registrada" if isinstance(self._backend, RegistroBackend) else "enviada"
        return AlertDelivery.objects.create(
            rule=rule, mensaje=mensaje, resultado=resultado,
            camara=camara, simulado=simulado
        )


def _valor_legible(event):
    if event.kind == "long_queue":
        return f"{round(event.value / 60)} min de espera"
    if event.kind == "empty_counter":
        return "sin nadie atendiendo"
    return f"{round(event.value)} personas"


def _mensaje_por_accion(rule, event):
    """Genera el mensaje según la acción de la regla."""
    if rule.accion == "avisar":
        return (f"[{event.camera.business.name}] {event.get_kind_display()} "
                f"en {event.zone_name}: {_valor_legible(event)}")

    defaults = {
        "abrir_caja": "Pedir a un empleado que abra la segunda caja",
        "mensaje_personal": f"Mensaje al personal: revisar {event.zone_name}",
        "registrar": "Registrado en el reporte",
    }
    base = rule.texto or defaults.get(rule.accion, "Acción operativa")
    return f"{base} — {event.get_kind_display()} en {event.zone_name}"


def notificar_evento(event, notifier=None, simulado=False):
    reglas = AlertRule.objects.filter(business=event.camera.business,
                                      tipo_evento=event.kind, activa=True)
    entregas = []
    for regla in reglas:
        msg = _mensaje_por_accion(regla, event)
        n = notifier or Notifier(backend_de(regla))
        entrega = n.notificar(regla, msg, camara=event.camera.name, simulado=simulado)
        entregas.append(entrega)
    return entregas