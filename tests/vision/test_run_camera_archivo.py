import cv2
import numpy as np
import pytest
import supervision as sv
from django.core.management import call_command

from analytics.models import MetricWindow
from cameras.models import Camera, Zone
from tenancy.models import Business


def generar_video(ruta, fps=2.0, frames=4, ancho=32, alto=24):
    writer = cv2.VideoWriter(str(ruta), cv2.VideoWriter_fourcc(*"mp4v"), fps, (ancho, alto))
    for _ in range(frames):
        writer.write(np.zeros((alto, ancho, 3), dtype=np.uint8))
    writer.release()


class FakeYolo:
    def __init__(self, model_path, imgsz, device="cpu", conf=0.3):
        pass

    def detect(self, frame):
        return sv.Detections.empty()


@pytest.fixture
def camara(tmp_path):
    biz = Business.objects.create(name="A", kind="cafe")
    cam = Camera.objects.create(business=biz, name="Tienda", source="0")
    Zone.objects.create(camera=cam, name="fila", kind="queue",
                        polygon=[[0, 0], [32, 0], [32, 24], [0, 24]])
    video = tmp_path / "tienda.mp4"
    generar_video(video)
    cam.source = f"file://{video}"
    cam.frame_w, cam.frame_h = 32, 24
    cam.save()
    return cam


@pytest.mark.django_db
def test_run_camera_procesa_un_archivo_y_persiste_metricas(camara, monkeypatch):
    import vision.management.commands.run_camera as rc
    monkeypatch.setattr(rc, "YoloDetector", FakeYolo)

    call_command("run_camera", camara.pk, "--una-pasada", "--window", "1", verbosity=0)

    assert MetricWindow.objects.filter(camera=camara).count() >= 1


@pytest.mark.django_db
def test_run_camera_rechaza_camara_sin_zonas(tmp_path, monkeypatch):
    biz = Business.objects.create(name="B", kind="cafe")
    cam = Camera.objects.create(business=biz, name="Sin zonas", source="0")

    with pytest.raises(Exception):
        call_command("run_camera", cam.pk, "--una-pasada", verbosity=0)


@pytest.mark.django_db
def test_un_clip_mas_corto_que_la_ventana_igual_persiste(camara, monkeypatch):
    import vision.management.commands.run_camera as rc
    monkeypatch.setattr(rc, "YoloDetector", FakeYolo)

    # el clip dura 2 s y la ventana pide 60: sin el cierre final no se guarda nada
    call_command("run_camera", camara.pk, "--una-pasada", "--window", "60", verbosity=0)

    assert MetricWindow.objects.filter(camera=camara).count() == 1

@pytest.mark.django_db
def test_las_cajas_guardadas_quedan_en_la_resolucion_de_referencia(tmp_path, monkeypatch):
    from cameras.models import Camera, Recorrido, Zone
    from tenancy.models import Business
    from vision.core import detector as mod

    biz = Business.objects.create(name="C", kind="cafe")
    cam = Camera.objects.create(business=biz, name="Ref distinta", source="0")
    Zone.objects.create(camera=cam, name="zona", kind="general",
                        polygon=[[0, 0], [1, 0], [1, 1], [0, 1]])
    # La cámara se calibró (zonas dibujadas) sobre un video de 200x200...
    cam.frame_w, cam.frame_h = 200, 200
    video = tmp_path / "chico.mp4"
    # ...pero el archivo que se analiza ahora mide 100x100.
    generar_video(video, ancho=100, alto=100, frames=6)
    cam.source = f"file://{video}"
    cam.save()

    caja_original = sv.Detections(
        xyxy=np.array([[10.0, 10.0, 30.0, 90.0]]),
        class_id=np.array([0]), confidence=np.array([0.9]),
        tracker_id=np.array([1]))
    monkeypatch.setattr(mod.YoloDetector, "detect", lambda self, f: caja_original)

    call_command("run_camera", cam.pk, "--una-pasada", "--window", "1", verbosity=0)

    recorrido = Recorrido.objects.get(camera=cam)
    x1, y1, x2, y2 = recorrido.pistas[0]["cajas"][0]["xyxy"]
    # Escalado por sx=sy=200/100=2: la caja que llegaba a x=30 de 100 (30%)
    # debe seguir en el 30% de la referencia de 200, es decir x=60.
    assert (x1, y1, x2, y2) == (20, 20, 60, 180)
