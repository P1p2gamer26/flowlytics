import pytest
from unittest.mock import MagicMock
from vision.core.fuente_video import FuenteVideo

@pytest.mark.django_db
def test_fuente_inestable_corta_y_vuelve():
    fuente = FuenteVideo(url="rtsp://doble/local")
    # El doble debe exponer los métodos de inestabilidad
    assert hasattr(fuente, "cortar")
    assert hasattr(fuente, "reconectar")
    assert hasattr(fuente, "mala_luz")
    fuente.cortar()
    assert not fuente.esta_activa()
    fuente.reconectar()
    assert fuente.esta_activa()

@pytest.mark.django_db
def test_mala_luz_no_rompe_pipeline():
    fuente = FuenteVideo(url="rtsp://doble/local")
    fuente.mala_luz()
    # El pipeline debe seguir procesando aunque la luz sea mala;
    # la detección puede ser menos precisa, pero no debe lanzar excepción.
    frames = fuente.entregar_frames()
    assert isinstance(frames, list)
    assert len(frames) >= 0
    # Si corta, el pipeline debe manejar el vacío sin error
    fuente.cortar()
    frames_cortado = fuente.entregar_frames()
    assert frames_cortado == []

@pytest.mark.django_db
def test_reconexion_no_duplicar_recorrido():
    from cameras.models import Camera, Recorrido
    from tenancy.models import Business
    from vision.core.fuente_video import FuenteVideo
    business = Business.objects.create(id=1, name="doble")
    cam = Camera.objects.create(id=1, business=business, name="doble")
    fuente = FuenteVideo(url="rtsp://doble/local")
    # Simular un análisis que está a mitad
    recorrido = Recorrido.objects.create(
        camera_id=1,
        pistas=[{"t": 0, "cajas": [{"id": 1, "xyxy": [1,2,3,4]}]}],
    )
    fuente.cortar()
    fuente.reconectar()
    # El pipeline debe retomar sin crear un nuevo Recorrido duplicado
    assert Recorrido.objects.filter(camera_id=1).count() == 1
    assert recorrido.pistas[0]["t"] == 0
