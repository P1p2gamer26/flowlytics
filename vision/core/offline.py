# vision/core/offline.py
from analytics.models import AlertDelivery, AlertRule, Event
from vision.core.events import avisos_sin_duplicados

class AcumuladorOffline:
    def __init__(self):
        pass

    def acumular(self, rule: AlertRule, evento: dict):
        # En una ronda futura: crear AlertDelivery con pendiente_sincronizacion=True
        mensaje = f"{rule.tipo_evento}: {evento.get('value')} @ {evento.get('zone_name')}"
        return mensaje

    def enviar_pendientes(self):
        # En una ronda futura: leer AlertDelivery con pendiente_sincronizacion=True,
        # aplicar avisos_sin_duplicados, enviar y marcar False
        pass
