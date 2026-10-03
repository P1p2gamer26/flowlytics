"""Evaluación de zonas poligonales sobre detecciones.

Recibe specs como diccionarios, no modelos de Django: así se testea sin base de datos.
"""
import numpy as np
import supervision as sv


class ZoneSet:
    def __init__(self, zones: dict[str, sv.PolygonZone]):
        self._zones = zones

    @classmethod
    def from_specs(cls, specs, frame_wh, ref_wh=None):
        """Construye las zonas.

        Los polígonos están en píxeles de la imagen de referencia (`ref_wh`, por
        ejemplo el frame con el que el dueño dibujó las zonas). Si el stream o el
        video llega con otra resolución, se escalan proporcionalmente para que las
        zonas sigan apuntando al mismo lugar.
        """
        w, h = frame_wh
        sx = sy = 1.0
        if ref_wh:
            rw, rh = ref_wh
            if rw and rh:
                sx, sy = w / rw, h / rh

        zones = {}
        for spec in specs:
            polygon = np.array(spec["polygon"], dtype=float)
            polygon[:, 0] *= sx
            polygon[:, 1] *= sy
            zones[spec["name"]] = sv.PolygonZone(
                polygon=polygon.astype(int),
                triggering_anchors=(sv.Position.BOTTOM_CENTER,),
            )
        return cls(zones)

    def evaluate(self, detections):
        counts, ids_by_zone = {}, {}
        for name, zone in self._zones.items():
            if len(detections) == 0:
                counts[name] = 0
                ids_by_zone[name] = set()
                continue

            mask = zone.trigger(detections)
            counts[name] = int(mask.sum())
            if detections.tracker_id is None:
                ids_by_zone[name] = set()
            else:
                ids_by_zone[name] = {int(t) for t in detections.tracker_id[mask]}
        return counts, ids_by_zone
