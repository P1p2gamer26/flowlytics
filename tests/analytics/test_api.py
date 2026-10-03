from datetime import date, datetime, timezone as dt_tz

import pytest
from django.contrib.auth.models import User

from analytics.models import MetricWindow
from cameras.models import Camera
from tenancy.models import Business, Profile


@pytest.fixture
def world(db):
    biz_a = Business.objects.create(name="A", kind="cafe")
    biz_b = Business.objects.create(name="B", kind="retail")
    cam_a = Camera.objects.create(business=biz_a, name="ca", source="0")
    cam_b = Camera.objects.create(business=biz_b, name="cb", source="0")

    def window(cam, hour, avg, mx, dwell, visitors, zone="fila", kind="queue"):
        start = datetime(2026, 8, 12, hour, 0, tzinfo=dt_tz.utc)
        end = datetime(2026, 8, 12, hour, 1, tzinfo=dt_tz.utc)
        MetricWindow.objects.create(camera=cam, zone_name=zone, zone_kind=kind,
                                    started_at=start, ended_at=end,
                                    occupancy_avg=avg, occupancy_max=mx,
                                    dwell_seconds=dwell, unique_visitors=visitors)

    window(cam_a, 9, 2.0, 3, 60.0, 5)
    window(cam_a, 13, 8.0, 12, 200.0, 20)
    window(cam_b, 9, 99.0, 99, 999.0, 99)

    owner_a = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=owner_a, role="owner", business=biz_a)
    admin = User.objects.create_user("root", password="x")
    Profile.objects.create(user=admin, role="admin")
    return dict(biz_a=biz_a, biz_b=biz_b, owner_a=owner_a, admin=admin)


@pytest.mark.django_db
def test_daily_summary_aggregates_only_that_business(world):
    from analytics.aggregates import daily_summary

    result = daily_summary(world["biz_a"], date(2026, 8, 12))

    assert result["total_visitors"] == 25       # 5 + 20, sin tocar biz_b
    assert result["peak_occupancy"] == 12
    assert result["peak_hour"] == 13
    assert result["avg_queue_seconds"] == 130.0  # (60 + 200) / 2


@pytest.mark.django_db
def test_owner_can_read_their_summary(api_client, world):
    api_client.force_authenticate(world["owner_a"])

    r = api_client.get("/api/summary/", {"business": world["biz_a"].pk,
                                         "date": "2026-08-12"})

    assert r.status_code == 200
    assert r.json()["total_visitors"] == 25


@pytest.mark.django_db
def test_owner_cannot_read_another_business(api_client, world):
    api_client.force_authenticate(world["owner_a"])

    r = api_client.get("/api/summary/", {"business": world["biz_b"].pk,
                                         "date": "2026-08-12"})

    assert r.status_code == 403


@pytest.mark.django_db
def test_admin_can_read_any_business(api_client, world):
    api_client.force_authenticate(world["admin"])

    r = api_client.get("/api/summary/", {"business": world["biz_b"].pk,
                                         "date": "2026-08-12"})

    assert r.status_code == 200
    assert r.json()["total_visitors"] == 99


@pytest.mark.django_db
def test_anonymous_is_rejected(api_client, world):
    r = api_client.get("/api/summary/", {"business": world["biz_a"].pk,
                                         "date": "2026-08-12"})

    assert r.status_code in (401, 403)
