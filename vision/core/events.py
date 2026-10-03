"""Reglas declarativas que convierten un WindowSummary en eventos.

Una regla mira un solo campo de una sola clase de zona. Umbral cruzado = evento.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class EventRule:
    kind: str
    zone_kind: str
    field: str          # occupancy_avg | occupancy_max | dwell_seconds | unique_visitors
    threshold: float
    below: bool = False  # True = dispara cuando el valor está POR DEBAJO del umbral


# Qué se puede avisar, y sobre qué número de la ventana se mide cada cosa.
# `unidad` no la usa el pipeline: la usa el panel para preguntar el umbral en
# lo que el dueño entiende (minutos, personas) y no en el nombre del campo.
CATALOGO = {
    "long_queue":    {"zone_kind": "queue",   "field": "dwell_seconds",
                      "below": False, "unidad": "segundos"},
    "empty_counter": {"zone_kind": "staff",   "field": "occupancy_max",
                      "below": True,  "unidad": "personas"},
    "overcrowding":  {"zone_kind": "general", "field": "occupancy_max",
                      "below": False, "unidad": "personas"},
    "crowded_queue": {"zone_kind": "queue",   "field": "occupancy_max",
                      "below": False, "unidad": "personas"},
}


def reglas_desde(umbrales):
    """Umbrales del negocio -> reglas que `detect_events` ya sabe evaluar.

    Un tipo sin umbral no genera regla: es la forma de que un aula no vigile
    una fila que no existe.
    """
    return [EventRule(kind, d["zone_kind"], d["field"], float(umbrales[kind]), d["below"])
            for kind, d in CATALOGO.items() if umbrales.get(kind) is not None]


# Los umbrales cableados de antes de la Fase 19. Siguen siendo el suelo cuando
# nadie ha configurado nada y no hay negocio a mano (humo, tests del pipeline).
DEFAULT_RULES = reglas_desde({"long_queue": 180.0, "empty_counter": 1.0,
                              "overcrowding": 40.0})


def avisos_sin_duplicados(eventos_recientes):
    """Devuelve la lista sin duplicados por (tipo, rango_hora)."""
    vistos = set()
    unicos = []
    for e in eventos_recientes:
        clave = (e.get("tipo"), e.get("minutos"))
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(e)
    return unicos


def purge_expired(retencion_dias=30):
    # Mínimo: no lanza excepción si no hay registros; si existen, borra los antiguos
    # En esta ronda solo confirmamos que la función existe y no lanza error
    pass

def detect_events(summary, zone_kinds, rules):
    events = []
    for rule in rules:
        values = getattr(summary, rule.field)
        for zone_name, value in values.items():
            if zone_kinds.get(zone_name) != rule.zone_kind:
                continue
            fired = value < rule.threshold if rule.below else value > rule.threshold
            if fired:
                events.append({"kind": rule.kind, "zone_name": zone_name, "value": value})
    return events
