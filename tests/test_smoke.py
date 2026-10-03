import pytest
from django.conf import settings


def test_settings_load_detector_config():
    assert settings.DETECTOR_IMGSZ == 640
    assert settings.SAMPLE_FPS == 2.0
    assert settings.DETECTOR_MODEL.startswith("yolov8n")


@pytest.mark.django_db
def test_database_reachable():
    from django.contrib.auth.models import User
    assert User.objects.count() == 0
