from datetime import datetime, time, timezone as dt_tz
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db.models import Avg, Max, Sum

from .models import CrossingWindow, MetricWindow


def _day_bounds(day, zona=None):
    """De medianoche a medianoche EN LA ZONA DEL NEGOCIO, devuelto en UTC.

    Fijar el dia en UTC parecia inofensivo y no lo era: en Bogota (UTC-5) todo
    lo que pasa a partir de las 19:00 cae en el dia UTC siguiente. Un dueno que
    abre el panel al cerrar veia "hoy no se ha registrado nadie" con la tienda
    llena de datos — medido el 6-sep-2026 con las tres camaras del banco.

    El dia de una tienda es el dia de la tienda, no el del meridiano de
    Greenwich. `Business.timezone` ya existia; simplemente no se usaba.
    """
    try:
        tz = ZoneInfo(zona) if zona else dt_tz.utc
    except (ZoneInfoNotFoundError, ValueError):
        # Una zona mal escrita no puede dejar el panel en blanco: se cae a UTC,
        # que es como se comportaba antes.
        tz = dt_tz.utc
    return (datetime.combine(day, time.min, tzinfo=tz).astimezone(dt_tz.utc),
            datetime.combine(day, time.max, tzinfo=tz).astimezone(dt_tz.utc))


def hoy_del_negocio(business):
    """Que dia es "hoy" para esta tienda.

    La otra mitad del mismo bug que arregla `_day_bounds`: no basta con acotar
    bien el dia si quien pregunta pide el dia equivocado. A las 20:00 en Bogota
    el servidor (UTC) ya esta en el dia siguiente, asi que `date.today()` le
    pedia al panel un dia en el que la tienda todavia no ha abierto.
    """
    from django.utils import timezone as dj_tz

    zona = getattr(business, "timezone", None)
    try:
        tz = ZoneInfo(zona) if zona else dt_tz.utc
    except (ZoneInfoNotFoundError, ValueError):
        tz = dt_tz.utc
    return dj_tz.now().astimezone(tz).date()


def daily_summary(business, day):
    start, end = _day_bounds(day, getattr(business, "timezone", None))
    windows = MetricWindow.objects.filter(
        camera__business=business, started_at__gte=start, started_at__lte=end
    )

    totals = windows.aggregate(visitors=Sum("unique_visitors"),
                               peak=Max("occupancy_max"))
    # Sum() devuelve None si no hay ninguna fila, y ese None se deja pasar tal
    # cual a propósito: "no hay línea dibujada" no es "entraron 0 personas".
    cruces = CrossingWindow.objects.filter(
        camera__business=business, started_at__gte=start, started_at__lte=end,
    ).aggregate(entradas=Sum("entradas"), salidas=Sum("salidas"))
    queue = windows.filter(zone_kind="queue").aggregate(avg=Avg("dwell_seconds"))
    # Permanencia donde está el cliente: fuera de la fila (eso es espera) y fuera
    # del área de personal (eso es turno, no visita). Es la métrica principal de
    # un café y de un restaurante.
    dwell = windows.exclude(zone_kind__in=("queue", "staff")).aggregate(
        avg=Avg("dwell_seconds"))
    staff = windows.filter(zone_kind="staff")
    staff_total = staff.count()
    staff_covered = staff.filter(occupancy_max__gte=1).count()

    hourly, peak_hour = [], None
    best = -1.0
    for hour in range(24):
        rows = windows.filter(started_at__hour=hour)
        if not rows.exists():
            continue
        agg = rows.aggregate(occ=Avg("occupancy_avg"), vis=Sum("unique_visitors"),
                             mx=Max("occupancy_max"))
        hourly.append({"hour": hour,
                       "occupancy_avg": round(agg["occ"], 2),
                       "visitors": agg["vis"] or 0})
        if agg["mx"] > best:
            best, peak_hour = agg["mx"], hour

    zones = [
        {"zone_name": z["zone_name"], "zone_kind": z["zone_kind"],
         "occupancy_avg": round(z["occ"], 2), "dwell_seconds": round(z["dwell"], 1),
         "visitors": z["vis"] or 0}
        for z in windows.values("zone_name", "zone_kind").annotate(
            occ=Avg("occupancy_avg"), dwell=Avg("dwell_seconds"),
            vis=Sum("unique_visitors")).order_by("zone_name")
    ]

    return {
        "date": day.isoformat(),
        "business": business.name,
        "total_visitors": totals["visitors"] or 0,
        "entradas": cruces["entradas"],
        "salidas": cruces["salidas"],
        "peak_occupancy": totals["peak"] or 0,
        "peak_hour": peak_hour,
        "avg_queue_seconds": round(queue["avg"], 1) if queue["avg"] is not None else None,
        "avg_dwell_seconds": round(dwell["avg"], 1) if dwell["avg"] is not None else None,
        "staff_coverage_pct": (round(100 * staff_covered / staff_total, 1)
                               if staff_total else None),
        "hourly": hourly,
        "zones": zones,
    }
