import numpy as np
import supervision as sv

from vision.core.detector import FakeDetector
from vision.core.events import EventRule
from vision.core.metrics import MetricAccumulator
from vision.core.zones import ZoneSet
from vision.pipeline import Pipeline

SPECS = [{"name": "fila", "kind": "queue",
          "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]]}]
ZONE_KINDS = {"fila": "queue"}


def dets(n):
    if n == 0:
        return sv.Detections.empty()
    xyxy = np.array([[10 + i * 5, 40, 14 + i * 5, 50] for i in range(n)], dtype=np.float32)
    return sv.Detections(
        xyxy=xyxy,
        class_id=np.zeros(n, dtype=int),
        confidence=np.full(n, 0.9, dtype=np.float32),
    )


def build(scripted, window=60, rules=None):
    return Pipeline(
        detector=FakeDetector(scripted),
        zone_set=ZoneSet.from_specs(SPECS, frame_wh=(200, 200)),
        zone_kinds=ZONE_KINDS,
        accumulator=MetricAccumulator(window_seconds=window),
        rules=rules if rules is not None else [],
        tracker=sv.ByteTrack(),
    )


def test_no_summary_before_window_closes():
    pipe = build([dets(2)])
    frame = np.zeros((200, 200, 3), dtype=np.uint8)

    result = pipe.process(frame, timestamp=0.0)

    assert result.summary is None
    assert result.events == []


def test_summary_emitted_when_window_closes():
    pipe = build([dets(2), dets(3)], window=10)
    frame = np.zeros((200, 200, 3), dtype=np.uint8)

    pipe.process(frame, timestamp=0.0)
    result = pipe.process(frame, timestamp=10.0)

    assert result.summary is not None
    assert result.summary.occupancy_max["fila"] == 3


def test_events_fire_from_the_summary():
    rule = EventRule("overcrowding", "queue", "occupancy_max", threshold=2)
    pipe = build([dets(1), dets(5)], window=10, rules=[rule])
    frame = np.zeros((200, 200, 3), dtype=np.uint8)

    pipe.process(frame, timestamp=0.0)
    result = pipe.process(frame, timestamp=10.0)

    assert [e["kind"] for e in result.events] == ["overcrowding"]


def test_tracker_assigns_ids_so_visitors_are_counted():
    pipe = build([dets(2), dets(2)], window=10)
    frame = np.zeros((200, 200, 3), dtype=np.uint8)

    pipe.process(frame, timestamp=0.0)
    result = pipe.process(frame, timestamp=10.0)

    assert result.summary.unique_visitors["fila"] >= 1


def test_el_tracker_por_defecto_sabe_a_que_ritmo_se_muestrea(settings):
    """Sin tracker explicito, el Pipeline debe usar la fabrica calibrada, no un
    ByteTrack crudo a 30 FPS."""
    from django.conf import settings as cfg
    from vision.pipeline import Pipeline

    p = Pipeline(detector=None, zone_set=None, zone_kinds={}, accumulator=None, rules={})
    assert p._tracker.minimum_consecutive_frames == 2
    assert p._tracker.max_time_lost == int((int(round(cfg.SAMPLE_FPS)) or 1) / 30.0 * 30)


