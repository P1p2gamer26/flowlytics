"""Reporte por negocio y por periodo. Función pura: recibe un Business y dos
fechas, devuelve una fila por día. Reutiliza daily_summary (aforo, cola,
visitantes) y le suma entradas/salidas de CrossingWindow, que no están en el
summary. Las vistas CSV y PDF se montan sobre esta única fuente.
"""
from datetime import timedelta

from django.db.models import Sum

from .aggregates import _day_bounds, daily_summary
from .models import CrossingWindow


def _dias(desde, hasta):
    dia = desde
    while dia <= hasta:
        yield dia
        dia += timedelta(days=1)


def reporte_periodo(business, desde, hasta):
    filas = []
    for dia in _dias(desde, hasta):
        s = daily_summary(business, dia)
        inicio, fin = _day_bounds(dia, getattr(business, "timezone", None))
        cruces = CrossingWindow.objects.filter(
            camera__business=business, started_at__gte=inicio, started_at__lte=fin,
        ).aggregate(entradas=Sum("entradas"), salidas=Sum("salidas"))
        filas.append({
            "fecha": dia.isoformat(),
            "visitantes": s["total_visitors"],
            "aforo_pico": s["peak_occupancy"],
            "hora_pico": s["peak_hour"],
            "cola_seg_prom": s["avg_queue_seconds"],
            "entradas": cruces["entradas"] or 0,
            "salidas": cruces["salidas"] or 0,
        })
    return filas
