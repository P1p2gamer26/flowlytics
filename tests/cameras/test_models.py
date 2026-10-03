import pytest
from django.core.exceptions import ValidationError

from cameras.models import Camera, Zone
from tenancy.models import Business


@pytest.fixture
def camera(db):
    biz = Business.objects.create(name="Cafe Uno", kind="cafe")
    return Camera.objects.create(business=biz, name="Barra", source="0")


@pytest.mark.django_db
def test_webcam_source_resolves_to_int(camera):
    assert camera.resolved_source == 0


@pytest.mark.django_db
def test_rtsp_source_stays_string(db):
    biz = Business.objects.create(name="B", kind="retail")
    cam = Camera.objects.create(business=biz, name="Puerta",
                                source="rtsp://10.0.0.5:554/stream")
    assert cam.resolved_source == "rtsp://10.0.0.5:554/stream"


@pytest.mark.django_db
def test_youtube_source_resolves_to_stream_url(db, monkeypatch):
    import cameras.models as cm
    monkeypatch.setattr(cm, "resolver_youtube", lambda url: "https://hls/" + url[-11:])
    biz = Business.objects.create(name="Y", kind="retail")
    cam = Camera.objects.create(business=biz, name="Caja",
                                source="https://www.youtube.com/watch?v=3o9aoRyrvAk")
    assert cam.resolved_source == "https://hls/3o9aoRyrvAk"


@pytest.mark.django_db
def test_zone_rejects_polygon_with_less_than_three_points(camera):
    zone = Zone(camera=camera, name="Fila", kind="queue", polygon=[[0, 0], [10, 0]])
    with pytest.raises(ValidationError):
        zone.full_clean()


@pytest.mark.django_db
def test_zone_accepts_valid_polygon(camera):
    zone = Zone(camera=camera, name="Fila", kind="queue",
                polygon=[[0, 0], [10, 0], [10, 10], [0, 10]])
    zone.full_clean()
    zone.save()
    assert zone.pk is not None
