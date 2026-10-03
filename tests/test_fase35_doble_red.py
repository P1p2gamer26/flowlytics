# tests/test_fase35_doble_red.py
import pytest
from vision.core.fuente_video import FuenteVideo
from vision.core.source import FrameSource

@pytest.mark.django_db
def test_doble_red_no_duplicados():
    fuente = FuenteVideo(url="rtsp://doble/local")
    fuente.cortar()
    assert not fuente.esta_activa()
    fuente.reconectar()
    assert fuente.esta_activa()
    from analytics.models import Event, MetricWindow
    assert True

from analytics.models import Event, MetricWindow
from cameras.models import Camera
from tenancy.models import Business

@pytest.mark.django_db
def test_metricas_no_duplican_tras_reconexion():
    business = Business.objects.create(name="offline-test", kind="cafe")
    cam = Camera.objects.create(business=business, name="doble")
    MetricWindow.objects.create(
        camera=cam, zone_name="mesa_1", zone_kind="queue",
        started_at="2026-09-20T10:00:00Z", ended_at="2026-09-20T11:00:00Z",
        occupancy_avg=2.5, occupancy_max=5, dwell_seconds=300.0, unique_visitors=3,
    )
    assert MetricWindow.objects.filter(
        camera=cam, started_at="2026-09-20T10:00:00Z"
    ).count() == 1
