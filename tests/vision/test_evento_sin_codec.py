import numpy as np
import pytest

from analytics.models import Event, EventClip
from cameras.models import Camera
from tenancy.models import Business
from vision.management.commands import run_camera
from vision.core.ringbuffer import FrameRingBuffer


class EscritorMudo:
    """Como el VideoWriter de una VM sin H.264: acepta frames y no escribe nada."""
    def __init__(self, *a, **k):
        pass

    def write(self, frame):
        pass

    def release(self):
        pass


@pytest.mark.django_db
def test_evento_sin_codec_se_guarda_sin_clip_y_no_tumba_el_worker(monkeypatch):
    monkeypatch.setattr(run_camera.cv2, "VideoWriter", EscritorMudo)
    monkeypatch.setattr("analytics.notifier.notificar_evento", lambda e: None)
    cam = Camera.objects.create(business=Business.objects.create(name="B"), name="C")
    buffer = FrameRingBuffer(seconds=1, fps=2)
    buffer.push(np.zeros((4, 4, 3), dtype=np.uint8))

    run_camera.Command()._save_event(
        cam, {"kind": "queue_long", "zone_name": "Fila", "value": 3.0}, buffer, (4, 4))

    assert Event.objects.filter(camera=cam).count() == 1
    assert not EventClip.objects.exists()
