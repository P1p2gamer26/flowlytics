"""run_camera arma el pipeline con los umbrales del negocio, no con los cableados."""
import pytest
from django.core.management import call_command

from analytics.models import AlertRule
from cameras.models import Camera, Zone
from tenancy.models import Business
from tests.vision.test_run_camera_archivo import FakeYolo, generar_video


@pytest.fixture
def camara(tmp_path, db):
    negocio = Business.objects.create(name="Café", kind="cafe")
    cam = Camera.objects.create(business=negocio, name="Barra", source="0")
    Zone.objects.create(camera=cam, name="fila", kind="queue",
                        polygon=[[0, 0], [32, 0], [32, 24], [0, 24]])
    video = tmp_path / "barra.mp4"
    generar_video(video)
    cam.source = f"file://{video}"
    cam.frame_w, cam.frame_h = 32, 24
    cam.save()
    return cam


@pytest.mark.django_db
def test_run_camera_usa_los_umbrales_del_negocio(camara, monkeypatch):
    AlertRule.objects.create(business=camara.business, tipo_evento="crowded_queue",
                             canal="email", destino="d@t.co", umbral=3.0)

    import vision.management.commands.run_camera as rc
    monkeypatch.setattr(rc, "YoloDetector", FakeYolo)
    visto = {}
    original = rc.Pipeline

    def espia(**kwargs):
        visto["rules"] = kwargs["rules"]
        return original(**kwargs)

    monkeypatch.setattr(rc, "Pipeline", espia)

    call_command("run_camera", camara.pk, "--una-pasada", "--window", "1", verbosity=0)

    umbrales = {r.kind: r.threshold for r in visto["rules"]}
    assert umbrales["crowded_queue"] == 3.0     # el que puso el dueño
    assert umbrales["long_queue"] == 240.0      # el del café, no los 180 de antes
