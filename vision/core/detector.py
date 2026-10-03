"""Frontera con el modelo de deteccion.

Unico modulo que importa ultralytics. Cambiar de modelo = cambiar este archivo.
"""
from typing import Protocol

import numpy as np
import supervision as sv

PERSON_CLASS_ID = 0  # COCO


def filter_persons(detections: sv.Detections) -> sv.Detections:
    if len(detections) == 0:
        return detections
    return detections[detections.class_id == PERSON_CLASS_ID]


class Detector(Protocol):
    def detect(self, frame: np.ndarray) -> sv.Detections:
        ...


class YoloDetector:
    def __init__(self, model_path: str, imgsz: int, device: str = "cpu", conf: float = 0.3):
        from ultralytics import YOLO  # import perezoso: los tests no necesitan torch

        self._model = YOLO(model_path)
        self._imgsz = imgsz
        self._device = device
        self._conf = conf

    def detect(self, frame: np.ndarray) -> sv.Detections:
        result = self._model.predict(
            frame,
            imgsz=self._imgsz,
            device=self._device,
            conf=self._conf,
            classes=[PERSON_CLASS_ID],
            verbose=False,
        )[0]
        return filter_persons(sv.Detections.from_ultralytics(result))


class FakeDetector:
    """Detector determinista para tests. Repite la ultima entrada al agotar el guion."""

    def __init__(self, scripted: list[sv.Detections]):
        if not scripted:
            raise ValueError("FakeDetector necesita al menos una entrada")
        self._scripted = scripted
        self._i = 0

    def detect(self, frame: np.ndarray) -> sv.Detections:
        item = self._scripted[min(self._i, len(self._scripted) - 1)]
        self._i += 1
        return item
