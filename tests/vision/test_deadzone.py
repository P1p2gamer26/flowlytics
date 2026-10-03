import numpy as np
import supervision as sv

from vision.core.deadzone import aplicar_zona_muerta


def _dets(anchors):
    """Cajas cuyo BOTTOM_CENTER es cada (cx, cy) de `anchors`."""
    xyxy = np.array([[cx - 5, cy - 40, cx + 5, cy] for cx, cy in anchors], dtype=float)
    return sv.Detections(xyxy=xyxy, tracker_id=np.arange(len(anchors)))


def _zona_cuadrado(x0, y0, x1, y1):
    poly = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
    return sv.PolygonZone(polygon=poly, triggering_anchors=(sv.Position.BOTTOM_CENTER,))


def test_descarta_lo_que_cae_en_la_zona_muerta():
    zona = _zona_cuadrado(0, 0, 100, 100)
    dets = _dets([(50, 50), (200, 200)])       # 1 dentro, 1 fuera
    fuera = aplicar_zona_muerta(dets, zona)
    assert len(fuera) == 1
    assert fuera.xyxy[0][0] == 195             # sobrevive la de (200, 200)


def test_sin_zona_no_toca_nada():
    dets = _dets([(50, 50), (200, 200)])
    assert len(aplicar_zona_muerta(dets, None)) == 2


def test_deteccion_vacia_no_revienta():
    assert len(aplicar_zona_muerta(sv.Detections.empty(), _zona_cuadrado(0, 0, 10, 10))) == 0
