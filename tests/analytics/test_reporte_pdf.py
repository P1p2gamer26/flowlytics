from datetime import datetime, timezone as dt_tz

import pytest
from django.contrib.auth.models import User

from analytics.models import MetricWindow
from cameras.models import Camera
from tenancy.models import Business, Profile


@pytest.fixture
def duena(db):
    biz = Business.objects.create(name="Neg", kind="cafe")
    cam = Camera.objects.create(business=biz, name="c", source="0")
    MetricWindow.objects.create(camera=cam, zone_name="sala", zone_kind="general",
                                started_at=datetime(2026, 8, 10, 12, tzinfo=dt_tz.utc),
                                ended_at=datetime(2026, 8, 10, 12, tzinfo=dt_tz.utc),
                                occupancy_avg=3.0, occupancy_max=5,
                                dwell_seconds=0.0, unique_visitors=8)
    user = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=user, role="owner", business=biz)
    return user, biz


@pytest.mark.django_db
def test_pdf_devuelve_un_pdf(client, duena):
    user, biz = duena
    client.force_login(user)
    r = client.get("/reporte/pdf/", {"business": biz.pk,
                                     "desde": "2026-08-10", "hasta": "2026-08-11"})
    assert r.status_code == 200
    assert r["Content-Type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"          # firma de archivo PDF
    assert "attachment" in r["Content-Disposition"]


@pytest.mark.django_db
def test_pdf_de_otro_negocio_es_403(client, duena):
    user, _ = duena
    otro = Business.objects.create(name="Ajeno", kind="retail")
    client.force_login(user)
    assert client.get("/reporte/pdf/", {"business": otro.pk}).status_code == 403
