"""El informe de una pasada de humo: qué vio el sistema en un video, en texto.

Lee la base y arma markdown. No abre video ni carga YOLO: el tamaño y el códec
del archivo se los pasa ya medidos el comando `humo`. Mismo reparto que
analytics.precision con reporte_precision: aquí lo que se prueba, allá lo que
toca OpenCV.
"""
from django.db.models import Avg, Max, Sum

from analytics.aggregates import daily_summary
from analytics.models import CrossingWindow, Event, MetricWindow


def resumen_de_camara(camera):
    """Totales de ESTA camara, no del negocio.

    `daily_summary` agrega por negocio y por dia, que es lo correcto para el panel
    y lo incorrecto para una prueba de humo: cada corrida crea una camara nueva
    dentro del mismo negocio, asi que el informe acababa sumando las corridas
    anteriores. Medido el 6-sep-2026: dijo 120 cuando la corrida conto 78.
    """
    ventanas = list(MetricWindow.objects.filter(camera=camera))
    if not ventanas:
        return {"total_visitors": 0, "peak_occupancy": 0,
                "peak_hour": None, "dwell_promedio": None}

    dwells = [w.dwell_seconds for w in ventanas if w.dwell_seconds is not None]
    pico = max(ventanas, key=lambda w: w.occupancy_max)
    return {
        "total_visitors": sum(w.unique_visitors or 0 for w in ventanas),
        "peak_occupancy": pico.occupancy_max,
        "peak_hour": pico.started_at.hour,
        "dwell_promedio": round(sum(dwells) / len(dwells), 1) if dwells else None,
    }


def datos_del_informe(camera, dia, video, avisos=(), muestras_sugerencia=None):
    """Todo lo que el informe necesita, en un dict. Solo consultas."""
    ventanas = MetricWindow.objects.filter(camera=camera)
    por_zona = [
        {"zona": z["zone_name"], "tipo": z["zone_kind"],
         "ocupacion_media": round(z["occ"], 2), "ocupacion_max": z["mx"],
         "permanencia": round(z["dwell"], 1), "visitantes": z["vis"] or 0}
        for z in ventanas.values("zone_name", "zone_kind").annotate(
            occ=Avg("occupancy_avg"), mx=Max("occupancy_max"),
            dwell=Avg("dwell_seconds"), vis=Sum("unique_visitors")
        ).order_by("zone_name")
    ]
    cruces = [
        {"linea": c["line_name"], "entradas": c["ent"] or 0, "salidas": c["sal"] or 0}
        for c in CrossingWindow.objects.filter(camera=camera).values("line_name")
        .annotate(ent=Sum("entradas"), sal=Sum("salidas")).order_by("line_name")
    ]
    return {
        "camara": camera.name,
        "fuente": camera.source,
        "dia": dia.isoformat(),
        "video": video,
        "zonas": [{"nombre": z.name, "tipo": z.contexto_efectivo,
                   "vertices": len(z.polygon)} for z in camera.zones.all()],
        "muestras_sugerencia": muestras_sugerencia,
        "ventanas": ventanas.count(),
        "degradadas": ventanas.filter(degradada=True).count(),
        "por_zona": por_zona,
        "cruces": cruces,
        "eventos": [{"cuando": e.occurred_at.strftime("%H:%M:%S"), "tipo": e.kind,
                     "zona": e.zone_name, "valor": e.value}
                    for e in Event.objects.filter(camera=camera).order_by("occurred_at")],
        "resumen": resumen_de_camara(camera),
        "avisos": list(avisos),
    }


def _tabla(cabeceras, filas):
    if not filas:
        return "_Nada._\n"
    lineas = ["| " + " | ".join(cabeceras) + " |",
              "|" + "|".join(["---"] * len(cabeceras)) + "|"]
    lineas += ["| " + " | ".join(str(c) for c in fila) + " |" for fila in filas]
    return "\n".join(lineas) + "\n"


def informe(datos):
    """Markdown para leer de arriba abajo: el video, las zonas, lo que contó."""
    v, r = datos["video"], datos["resumen"]
    partes = [
        f"# Informe de humo — {datos['camara']}",
        "",
        f"Video: `{datos['fuente']}`  ",
        f"Día analizado: {datos['dia']}",
        "",
        "## El video",
        "",
        _tabla(["Dato", "Valor"], [
            ("Resolución", f"{v['ancho']}×{v['alto']}"),
            ("FPS", v["fps"]),
            ("Duración", f"{v['duracion_s']} s"),
            ("Frames", v["frames"]),
            ("H.264 (lo reproduce el navegador)", "sí" if v["h264"] else "no"),
        ]),
        "## Zonas",
        "",
        _tabla(["Zona", "Tipo", "Vértices"],
               [(z["nombre"], z["tipo"], z["vertices"]) for z in datos["zonas"]]),
    ]
    if datos["muestras_sugerencia"] is not None:
        partes += [f"Polígono sugerido a partir de {datos['muestras_sugerencia']} "
                   "detecciones.", ""]
    pico = (f" a las {r['peak_hour']}:00" if r["peak_hour"] is not None else "")
    partes += [
        "## Lo que contó",
        "",
        f"- Ventanas cerradas: **{datos['ventanas']}** "
        f"({datos['degradadas']} degradadas)",
        f"- Visitantes únicos del día: **{r['total_visitors']}**",
        f"- Aforo pico: **{r['peak_occupancy']}**{pico}",
        f"- Espera media en fila: {r.get('avg_queue_seconds', '—')} s",
        f"- Cobertura de personal: {r.get('staff_coverage_pct', '—')} %",
        "",
        _tabla(["Zona", "Tipo", "Ocupación media", "Ocupación máx",
                "Permanencia (s)", "Visitantes"],
               [(z["zona"], z["tipo"], z["ocupacion_media"], z["ocupacion_max"],
                 z["permanencia"], z["visitantes"]) for z in datos["por_zona"]]),
        "## Cruces de línea",
        "",
        _tabla(["Línea", "Entradas", "Salidas"],
               [(c["linea"], c["entradas"], c["salidas"]) for c in datos["cruces"]]),
        "## Eventos",
        "",
        _tabla(["Hora", "Tipo", "Zona", "Valor"],
               [(e["cuando"], e["tipo"], e["zona"], e["valor"]) for e in datos["eventos"]]),
        "## Avisos",
        "",
    ]
    partes += [f"- {a}" for a in datos["avisos"]] or ["Ninguno."]
    if datos["ventanas"] == 0:
        partes += ["", "**No se cerró ninguna ventana.** O el video no tiene gente, o no "
                   "se pudo leer: los avisos de arriba dicen cuál de las dos."]

    if datos.get("estabilidad") is not None:
        est = datos["estabilidad"]
        if est["medidas"]:
            partes += [
                "",
                "## Estabilidad del conteo",
                "",
                _tabla(["FPS", "Visitantes"],
                       [(fps, vis) for fps, vis in sorted(est["medidas"].items())]),
            ]
            if est["desvio_pct"] is not None:
                if est["estable"]:
                    veredicto = f"Desvío: {est['desvio_pct']:.1f} % — dentro de la tolerancia del 25 %."
                else:
                    veredicto = f"Desvío: {est['desvio_pct']:.1f} % — **el conteo depende del muestreo, no es fiable todavía.**"
                partes += [veredicto]

    if datos.get("anotado") is not None:
        a = datos["anotado"]
        partes += [
            "",
            "## Lo que vio el detector",
            "",
            (f"{a['cantidad']} muestras en `demo/humo_frames/{a['nombre']}/`. "
             "Cada caja es una persona y el número es su id de rastreo: "
             "si la misma persona cambia de número entre muestras, el rastreo se está partiendo."),
        ]

    return "\n".join(partes) + "\n"


# Tolerancia del 25 %: por debajo de eso la diferencia puede ser del muestreo
# viendo a alguien que el otro no llego a ver. Por encima, el conteo depende de
# como se mira y no del local, que es el bug de la Fase 11.
TOLERANCIA_PCT = 25.0


def comparar_muestreos(medidas):
    """`medidas` es {fps: visitantes}. Devuelve cuanto se desvia el conteo.

    El desvio se mide contra el valor mas bajo: si a 2 FPS ve 42 y a 6 ve 120,
    la pregunta que importa es cuanto INFLA el muestreo fino, no la media.
    """
    valores = [v for v in medidas.values() if v is not None]
    if len(valores) < 2:
        return {"estable": None, "desvio_pct": None, "medidas": medidas}
    bajo, alto = min(valores), max(valores)
    desvio = 100.0 * (alto - bajo) / bajo if bajo else float("inf")
    return {"estable": desvio <= TOLERANCIA_PCT, "desvio_pct": round(desvio, 1),
            "medidas": medidas}

