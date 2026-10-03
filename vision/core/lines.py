"""Conteo de cruces de línea (entrada/salida) sobre detecciones rastreadas.

Envuelve sv.LineZone igual que ZoneSet envuelve PolygonZone: recibe specs como
diccionarios (no modelos de Django) y escala los puntos desde la resolución de
referencia, para poder testear sin base de datos ni frames reales.

sv.LineZone mantiene su propio estado entre llamadas a trigger(): un cruce se
detecta cuando el anchor de un tracker pasa de un lado al otro entre dos frames.

La convención de sentido la fija sv.LineZone y está clavada por
`tests/vision/test_lines.py::test_convencion_de_sentido_la_salida_es_a_la_derecha_del_vector_ab`:
cruzar la línea pasando al lado izquierdo del vector A→B (en coordenadas normales, o
hacia arriba/y decreciente para A→B horizontal hacia la derecha) es una ENTRADA.
Cruzar al lado derecho del vector A→B es una SALIDA.
El editor del panel dibuja la flecha con esa misma regla, y `invertir` es lo que
la corrige cuando en un local concreto la puerta quedó del otro lado.
"""
import supervision as sv


class LineSet:
    def __init__(self, lines):
        # {nombre: (sv.LineZone, invertir)}
        self._lines = lines

    @classmethod
    def from_specs(cls, specs, frame_wh, ref_wh=None):
        w, h = frame_wh
        sx = sy = 1.0
        if ref_wh:
            rw, rh = ref_wh
            if rw and rh:
                sx, sy = w / rw, h / rh

        lines = {}
        for spec in specs:
            (ax, ay), (bx, by) = spec["puntos"]
            zona = sv.LineZone(
                start=sv.Point(ax * sx, ay * sy),
                end=sv.Point(bx * sx, by * sy),
                triggering_anchors=(sv.Position.BOTTOM_CENTER,),
            )
            lines[spec["name"]] = (zona, bool(spec.get("invertir", False)))
        return cls(lines)

    def update(self, detections):
        """Cruces de este frame: {nombre: (entradas_delta, salidas_delta)}."""
        deltas = {}
        for name, (zona, invertir) in self._lines.items():
            if len(detections) == 0 or detections.tracker_id is None:
                deltas[name] = (0, 0)
                continue
            cruzo_in, cruzo_out = zona.trigger(detections)
            ins, outs = int(cruzo_in.sum()), int(cruzo_out.sum())
            deltas[name] = (outs, ins) if invertir else (ins, outs)
        return deltas
