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
def test_csv_devuelve_adjunto_con_filas(client, duena):
    user, biz = duena
    client.force_login(user)
    r = client.get("/reporte/csv/", {"business": biz.pk,
                                     "desde": "2026-08-10", "hasta": "2026-08-10"})
    assert r.status_code == 200
    assert r["Content-Type"].startswith("text/csv")
    assert "attachment" in r["Content-Disposition"]
    cuerpo = r.content.decode()
    assert "fecha" in cuerpo                # cabecera
    assert "2026-08-10" in cuerpo and ",8" in cuerpo   # fila con 8 visitantes


@pytest.mark.django_db
def test_csv_de_otro_negocio_es_403(client, duena):
    user, _ = duena
    otro = Business.objects.create(name="Ajeno", kind="retail")
    client.force_login(user)
    r = client.get("/reporte/csv/", {"business": otro.pk})
    assert r.status_code == 403
