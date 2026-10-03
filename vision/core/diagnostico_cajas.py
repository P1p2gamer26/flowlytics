"""Diagnóstico numérico de `Recorrido.pistas`, sin abrir video ni cargar YOLO.

Mide, no arregla: sirve para decidir si el bug de la Fase 18 es de escala
(cajas guardadas en la resolución del frame en vez de la de referencia de la
cámara, el mismo patrón que ya corrigen `ZoneSet`/`LineSet`/`_acumular_pisadas`)
o de continuidad de identidad (un `track_id` que salta de posición al
reasignarse, señal de fragmentación de tracking, no de dibujo).
"""
from vision.core.geometria import pie_de_caja

def diagnosticar_pistas(pistas, frame_wh, ref_wh):
    fw, fh = frame_wh
    rw, rh = ref_wh
    necesita_reescalar = (fw, fh) != (rw, rh)

    fuera_de_referencia = 0
    puntos_por_track = {}
    for instante in pistas:
        for caja in instante.get("cajas", []):
            x1, y1, x2, y2 = caja["xyxy"]
            if x2 > rw or y2 > rh or x1 < 0 or y1 < 0:
                fuera_de_referencia += 1
            x, y = pie_de_caja(caja["xyxy"])
            puntos_por_track.setdefault(caja["id"], []).append((instante["t"], x, y))

    saltos = {}
    for track_id, puntos in puntos_por_track.items():
        puntos.sort(key=lambda p: p[0])
        maximo = 0.0
        for (_, x1, y1), (_, x2, y2) in zip(puntos, puntos[1:]):
            maximo = max(maximo, ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)
        saltos[track_id] = maximo

    return {
        "necesita_reescalar": necesita_reescalar,
        "cajas_fuera_de_referencia": fuera_de_referencia,
        "salto_maximo_por_track": saltos,
    }
