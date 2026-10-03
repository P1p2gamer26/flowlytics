"""Agrega las ventanas de calor de una cámara en un periodo, opcionalmente
restringido a una franja horaria (mañana/tarde), sumando las rejillas celda a
celda. Reusa `_day_bounds` de `aggregates.py`: el día de una tienda es el día
de la tienda, no el del meridiano de Greenwich — el mismo bug que ya se
arregló ahí aplicaría aquí si se reinventara.
"""
from datetime import datetime, time, timedelta
from datetime import timezone as dt_tz
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from vision.core.heatmap import UMBRAL_PERSONAS, normalizar, suavizar, sumar_grids

from .aggregates import _day_bounds
from .models import HeatmapWindow

FRANJAS = {"manana": (time(6, 0), time(14, 0)), "tarde": (time(14, 0), time(22, 0))}


def _bounds_franja(dia, franja, zona):
    try:
        tz = ZoneInfo(zona) if zona else dt_tz.utc
    except (ZoneInfoNotFoundError, ValueError):
        tz = dt_tz.utc
    ini_hora, fin_hora = FRANJAS[franja]
    return (datetime.combine(dia, ini_hora, tzinfo=tz).astimezone(dt_tz.utc),
            datetime.combine(dia, fin_hora, tzinfo=tz).astimezone(dt_tz.utc))


def mapa_calor_periodo(camera, desde, hasta, franja=None):
    """Suma las rejillas guardadas de `camera` entre `desde` y `hasta`
    (fechas, inclusive), opcionalmente restringido a `franja`
    ('manana'/'tarde'). Devuelve `{"grid": [...], "personas": N, "mensaje": ""}`;
    `grid` viene vacío y `mensaje` explica por qué cuando no hay análisis o no
    hay gente suficiente para que el mapa signifique algo.
    """
    zona = getattr(camera.business, "timezone", None)
    ventanas = []
    dia = desde
    while dia <= hasta:
        if franja:
            inicio, fin = _bounds_franja(dia, franja, zona)
        else:
            inicio, fin = _day_bounds(dia, zona)
        ventanas += list(
            HeatmapWindow.objects.filter(camera=camera, started_at__gte=inicio,
                                        started_at__lte=fin))
        dia += timedelta(days=1)

    if not ventanas:
        return {"grid": [], "personas": 0, "mensaje": "Sin análisis en este periodo."}

    grid, personas, descartadas = sumar_grids(
        [(v.counts, v.grid_rows, v.grid_cols, v.personas) for v in ventanas])

    if personas < UMBRAL_PERSONAS:
        return {
            "grid": [], "personas": personas,
            "mensaje": (f"Solo se vieron {personas} personas en este periodo: "
                       f"hacen falta al menos {UMBRAL_PERSONAS} para que el mapa "
                       "signifique algo y no sea ruido de un puñado de visitas."),
        }

    return {"grid": normalizar(suavizar(grid)), "personas": personas, "mensaje": ""}
