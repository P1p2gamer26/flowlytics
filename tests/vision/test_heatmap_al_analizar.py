import numpy as np
import pytest
import supervision as sv


@pytest.mark.django_db
def test_una_pasada_deja_al_menos_una_ventana_de_calor(camara_demo, monkeypatch):
    """Con un detector doble que siempre pone a alguien en el mismo sitio, la
    ventana de calor tiene que registrar esa pisada."""
    from django.core.management import call_command

    from analytics.models import HeatmapWindow
    from vision.core import detector as mod

    def _una_persona(_frame):
        return sv.Detections(xyxy=np.array([[10.0, 20.0, 50.0, 120.0]]),
                             class_id=np.array([0]), confidence=np.array([0.9]))

    monkeypatch.setattr(mod.YoloDetector, "detect", lambda self, f: _una_persona(f))
    call_command("run_camera", camara_demo.pk, "--una-pasada", "--window", "1")

    ventanas = HeatmapWindow.objects.filter(camera=camara_demo)
    assert ventanas.exists(), "el analisis no guardo ninguna ventana de calor"
    total_pisadas = sum(sum(fila) for v in ventanas for fila in v.counts)
    assert total_pisadas > 0
