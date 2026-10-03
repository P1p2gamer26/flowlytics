"""Descarta detecciones en la zona muerta de la cámara (near-field, reflejos, un
mostrador que el modelo confunde con una persona). Reutiliza sv.PolygonZone: una
detección se descarta si su anchor cae DENTRO del polígono.
"""


def aplicar_zona_muerta(detections, zona):
    if zona is None or len(detections) == 0:
        return detections
    dentro = zona.trigger(detections)
    return detections[~dentro]
