import numpy as np
import supervision as sv

from vision.core.detector import FakeDetector, filter_persons


def make_detections(class_ids, confidences=None):
    n = len(class_ids)
    return sv.Detections(
        xyxy=np.array([[0.0, 0.0, 10.0, 10.0]] * n, dtype=np.float32).reshape(n, 4),
        class_id=np.array(class_ids, dtype=int),
        confidence=np.array(confidences or [0.9] * n, dtype=np.float32),
    )


def test_filter_persons_keeps_only_class_zero():
    dets = make_detections([0, 2, 0, 15])

    result = filter_persons(dets)

    assert len(result) == 2
    assert set(result.class_id.tolist()) == {0}


def test_filter_persons_on_empty_detections():
    empty = sv.Detections.empty()

    result = filter_persons(empty)

    assert len(result) == 0


def test_fake_detector_replays_scripted_frames():
    a = make_detections([0])
    b = make_detections([0, 0])
    detector = FakeDetector([a, b])
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    assert len(detector.detect(frame)) == 1
    assert len(detector.detect(frame)) == 2


def test_fake_detector_repeats_last_when_script_exhausted():
    detector = FakeDetector([make_detections([0, 0])])
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    detector.detect(frame)
    assert len(detector.detect(frame)) == 2
