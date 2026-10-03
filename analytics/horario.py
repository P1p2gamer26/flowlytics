# analytics/horario.py
"""Si el local está abierto ahora mismo, en su zona horaria.

Mismo problema que resolvió `hoy_del_negocio` en `analytics/aggregates.py`: el
servidor va en UTC y el local no. A las 03:00 de Bogotá el servidor cree que son
las 08:00, que es una hora perfectamente razonable para mandar un aviso.
"""
from zoneinfo import ZoneInfo


def _hora_local(business, momento):
    try:
        zona = ZoneInfo(getattr(business, "timezone", "") or "UTC")
    except Exception:
        zona = ZoneInfo("UTC")
    return momento.astimezone(zona).time()


def en_horario(business, momento):
    """¿Está abierto el negocio en ese instante?

    `abre == cierra` significa "a cualquier hora": es el valor por defecto y
    deja el comportamiento de antes de la Fase 19 para quien no configure nada.
    """
    abre = getattr(business, "abre", None)
    cierra = getattr(business, "cierra", None)
    if abre is None or cierra is None or abre == cierra:
        return True

    ahora = _hora_local(business, momento)
    if abre < cierra:
        return abre <= ahora < cierra
    # Horario que cruza la medianoche: abre a las 18:00 y cierra a las 02:00.
    return ahora >= abre or ahora < cierra
