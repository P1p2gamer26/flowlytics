from datetime import timedelta

import pytest
from django.core.files.base import ContentFile
from django.utils import timezone

from analytics.models import Event, EventClip, MetricWindow
from cameras.models import Camera
from tenancy.models import Business
from vision.core.metrics import WindowSummary


@pytest.fixture
def camera(db):
    biz = Business.objects.create(name="Cafe Uno", kind="cafe")
    return Camera.objects.create(business=biz, name="Barra", source="0")


@pytest.fixture
def summary():
    return WindowSummary(
        started_at=1_700_000_000.0,
        ended_at=1_700_000_060.0,
        samples=120,
        occupancy_avg={"fila": 3.5, "barra": 1.0},
        occupancy_max={"fila": 7, "barra": 2},
        dwell_seconds={"fila": 95.0, "barra": 300.0},
        unique_visitors={"fila": 12, "barra": 2},
        crossings={},
    )


@pytest.mark.django_db
def test_from_summary_creates_one_row_per_zone(camera, summary):
    rows = MetricWindow.from_summary(camera, summary,
                                     zone_kinds={"fila": "queue", "barra": "staff"})

    assert len(rows) == 2
    assert MetricWindow.objects.count() == 2
    fila = MetricWindow.objects.get(zone_name="fila")
    assert fila.occupancy_max == 7
    assert fila.dwell_seconds == 95.0
    assert fila.zone_kind == "queue"


@pytest.mark.django_db
def test_from_summary_converts_epoch_to_aware_datetime(camera, summary):
    rows = MetricWindow.from_summary(camera, summary, zone_kinds={"fila": "queue",
                                                                 "barra": "staff"})

    assert timezone.is_aware(rows[0].started_at)
    assert (rows[0].ended_at - rows[0].started_at).total_seconds() == 60.0


@pytest.mark.django_db
def test_purge_expired_deletes_only_old_clips(camera):
    now = timezone.now()
    fresh = Event.objects.create(camera=camera, kind="long_queue",
                                 zone_name="fila", value=9.0, occurred_at=now)
    stale = Event.objects.create(camera=camera, kind="long_queue",
                                 zone_name="fila", value=9.0, occurred_at=now)
    for event, expires in ((fresh, now + timedelta(days=5)),
                           (stale, now - timedelta(days=1))):
        clip = EventClip(event=event, expires_at=expires)
        clip.file.save(f"{event.pk}.mp4", ContentFile(b"fake"), save=True)

    deleted = EventClip.purge_expired()

    assert deleted == 1
    assert EventClip.objects.count() == 1
    assert EventClip.objects.first().event == fresh
