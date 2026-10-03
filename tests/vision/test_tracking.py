import numpy as np
import supervision as sv

from vision.core.tracking import crear_tracker


def _det(cx, tid_box=None):
    """Persona moviéndose horizontalmente; caja 40x80 centrada en (cx, 100)."""
    xyxy = np.array([[cx - 20, 60, cx + 20, 140]], dtype=float)
    return sv.Detections(xyxy=xyxy, class_id=np.array([0]), confidence=np.array([0.9]))


def _vacio():
    return sv.Detections.empty()


def _ids(tracker, detecciones):
    out = tracker.update_with_detections(detecciones)
    return list(out.tracker_id) if out.tracker_id is not None else []


def test_buffer_largo_conserva_el_id_tras_una_oclusion():
    tracker = crear_tracker(fps=10, lost_track_buffer=30)
    # aparición y confirmación
    _ids(tracker, _det(50)); _ids(tracker, _det(60))
    ids_antes = _ids(tracker, _det(70))
    # oclusión: 3 frames sin detección
    for _ in range(3):
        _ids(tracker, _vacio())
    # reaparece donde el movimiento lo predice
    ids_despues = _ids(tracker, _det(100))

    assert ids_antes and ids_despues
    assert ids_despues[0] == ids_antes[0]      # mismo id: no contó una persona nueva


def test_configura_el_buffer_que_se_le_pasa():
    # esta version de supervision no guarda lost_track_buffer tal cual; lo
    # traduce a max_time_lost = frame_rate/30 * lost_track_buffer.
    tracker = crear_tracker(fps=10, lost_track_buffer=99)
    assert tracker.max_time_lost == int(10 / 30.0 * 99)
