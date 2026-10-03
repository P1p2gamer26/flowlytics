"""Un worker de cámara en vivo, sin cámara y sin red.

`cv2.VideoCapture` se sustituye por `FuenteFalsa` y el sleep del backoff por un
no-op: la prueba no espera segundos de verdad ni abre un socket.
"""
import numpy as np
import pytest
import supervision as sv
from django.core.management import call_command

import vision.core.source as source_mod
import vision.management.commands.run_camera as rc
from cameras.models import Camera, CameraHealth, Zone
from tenancy.models import Business
from vision.core.source import FuenteFalsa


class FakeYolo:
    def __init__(self, model_path, imgsz, device="cpu", conf=0.3):
        pass

    def detect(self, frame):
        return sv.Detections.empty()


def frame():
    return np.zeros((24, 32, 3), dtype=np.uint8)


@pytest.fixture
def camara_en_vivo(db):
    biz = Business.objects.create(name="A", kind="retail")
    cam = Camera.objects.create(business=biz, name="Puerta",
                                source="rtsp://10.0.0.5:554/stream1",
                                frame_w=32, frame_h=24)
    Zone.objects.create(camera=cam, name="entrada", kind="entrada",
                        polygon=[[0, 0], [32, 0], [32, 24], [0, 24]])
    return cam


@pytest.mark.django_db
def test_el_worker_sobrevive_a_un_corte_y_deja_dicho_por_que(camara_en_vivo, monkeypatch,
                                                             settings):
    settings.SAMPLE_FPS = 2
    aperturas = []

    def abrir_falso(*args, **kwargs):
        aperturas.append(1)
        guion = [frame()] if len(aperturas) <= 2 else [frame()] * 200
        return FuenteFalsa(guion, fps=2.0, ancho=32, alto=24)

    monkeypatch.setattr(rc.cv2, "VideoCapture", abrir_falso)
    monkeypatch.setattr(source_mod.time, "sleep", lambda s: None)
    monkeypatch.setattr(rc.time, "sleep", lambda s: None)
    monkeypatch.setattr(rc, "YoloDetector", FakeYolo)

    call_command("run_camera", camara_en_vivo.pk, "--max-seconds", "5.0",
                 "--window", "1", verbosity=0)

    salud = CameraHealth.objects.get(camera=camara_en_vivo)
    assert salud.reconexiones >= 1
    assert "sin señal" in salud.ultimo_error
    assert len(aperturas) >= 3