import numpy as np
import supervision as sv

from vision.core.lines import LineSet
from vision.core.metrics import MetricAccumulator
from vision.core.detector import FakeDetector
from vision.pipeline import Pipeline


def _det(cy, tid=1):
    xyxy = np.array([[90, cy - 20, 110, cy + 20]], dtype=float)
    return sv.Detections(xyxy=xyxy, class_id=np.array([0]), confidence=np.array([0.9]),
                         tracker_id=np.array([tid]))


def test_el_pipeline_reporta_cruces_en_el_summary():
    # el track baja gradualmente y cruza la línea a y=100. Pasos cortos para que
    # sv.ByteTrack (matching por IOU) conserve el mismo tracker_id cuadro a cuadro.
    posiciones = [20, 40, 60, 80, 100, 120, 140]
    detector = FakeDetector([_det(cy) for cy in posiciones])
    line_set = LineSet.from_specs(
        [{"name": "puerta", "puntos": [[0, 100], [200, 100]], "invertir": False}],
        frame_wh=(200, 200))
    pipeline = Pipeline(
        detector=detector, zone_set=_ZonasVacias(), zone_kinds={},
        accumulator=MetricAccumulator(window_seconds=len(posiciones)), rules=[],
        line_set=line_set, tracker=sv.ByteTrack())

    result = None
    for i in range(len(posiciones)):
        result = pipeline.process(_frame(), timestamp=float(i))
    result = pipeline.process(_frame(), timestamp=float(len(posiciones)))  # cierra la ventana

    assert result.summary is not None
    total = sum(sum(v) for v in result.summary.crossings.values())
    assert total >= 1


class _ZonasVacias:
    def evaluate(self, detections):
        return {}, {}


def _frame():
    return np.zeros((200, 200, 3), dtype=np.uint8)
