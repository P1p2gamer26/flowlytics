import numpy as np
import supervision as sv

from vision.core.zones import ZoneSet

SPECS = [
    {"name": "fila", "kind": "queue", "polygon": [[0, 0], [50, 0], [50, 100], [0, 100]]},
    {"name": "barra", "kind": "staff", "polygon": [[50, 0], [100, 0], [100, 100], [50, 100]]},
]


def dets_at(points, tracker_ids):
    """Cajas de 4x4 centradas en x, con el borde inferior en y."""
    xyxy = np.array([[x - 2, y - 4, x + 2, y] for x, y in points], dtype=np.float32)
    return sv.Detections(
        xyxy=xyxy,
        class_id=np.zeros(len(points), dtype=int),
        confidence=np.full(len(points), 0.9, dtype=np.float32),
        tracker_id=np.array(tracker_ids, dtype=int),
    )


def test_assigns_detections_to_the_correct_zone():
    zones = ZoneSet.from_specs(SPECS, frame_wh=(100, 100))

    counts, ids = zones.evaluate(dets_at([(25, 50), (75, 50)], [1, 2]))

    assert counts == {"fila": 1, "barra": 1}
    assert ids["fila"] == {1}
    assert ids["barra"] == {2}


def test_detection_outside_every_zone_is_counted_nowhere():
    zones = ZoneSet.from_specs(SPECS, frame_wh=(200, 200))

    counts, ids = zones.evaluate(dets_at([(150, 150)], [7]))

    assert counts == {"fila": 0, "barra": 0}
    assert ids["fila"] == set()


def test_empty_detections_yield_zero_counts():
    zones = ZoneSet.from_specs(SPECS, frame_wh=(100, 100))

    counts, ids = zones.evaluate(sv.Detections.empty())

    assert counts == {"fila": 0, "barra": 0}
    assert ids == {"fila": set(), "barra": set()}


def test_detections_without_tracker_ids_still_count():
    zones = ZoneSet.from_specs(SPECS, frame_wh=(100, 100))
    d = dets_at([(25, 50)], [1])
    d.tracker_id = None

    counts, ids = zones.evaluate(d)

    assert counts["fila"] == 1
    assert ids["fila"] == set()


def test_escala_las_zonas_cuando_la_resolucion_cambia():
    # zonas dibujadas sobre un frame de 100x100, video a 200x200
    zones = ZoneSet.from_specs(SPECS, frame_wh=(200, 200), ref_wh=(100, 100))

    counts, ids = zones.evaluate(dets_at([(50, 100), (150, 100)], [1, 2]))

    assert counts == {"fila": 1, "barra": 1}
    assert ids["fila"] == {1}
    assert ids["barra"] == {2}


def test_sin_ref_wh_las_zonas_se_usan_tal_cual():
    zones = ZoneSet.from_specs(SPECS, frame_wh=(100, 100), ref_wh=None)

    counts, _ = zones.evaluate(dets_at([(25, 50)], [1]))

    assert counts["fila"] == 1
