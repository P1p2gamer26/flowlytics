"""Pruebas del filtro ?minutos= en /api/camaras/<id>/trayectorias/."""
import pytest
from datetime import timedelta
from django.utils import timezone

from analytics.models import Trajectory
from cameras.models import Camera
from tenancy.models import Business, Plan, Profile
from django.contrib.auth.models import User


@pytest.mark.django_db
def test_trayectorias_minutos_filtra_por_fecha(api_client):
    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    a = Business.objects.create(name="A", kind="retail", plan=plan)
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    api_client.force_authenticate(ana)

    cam = Camera.objects.create(business=a, name="Cam", source="0")

    ahora = timezone.now()
    hace_10 = ahora - timedelta(minutes=10)
    hace_60 = ahora - timedelta(minutes=60)

    Trajectory.objects.create(
        camera=cam, started_at=hace_10, ended_at=hace_10 + timedelta(seconds=30),
        track_id=1, points=[[10, 20], [12, 22]], duration=30.0)
    Trajectory.objects.create(
        camera=cam, started_at=hace_60, ended_at=hace_60 + timedelta(seconds=30),
        track_id=2, points=[[30, 40], [32, 42]], duration=30.0)

    r = api_client.get(f"/api/camaras/{cam.pk}/trayectorias/?minutos=30")

    assert r.status_code == 200
    assert len(r.data["recorridos"]) == 1
    assert r.data["recorridos"][0]["track_id"] == 1


@pytest.mark.django_db
def test_trayectorias_sin_minutos_devuelve_todas(api_client):
    from tenancy.models import Plan
    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    a = Business.objects.create(name="A", kind="retail", plan=plan)
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    api_client.force_authenticate(ana)

    cam = Camera.objects.create(business=a, name="Cam", source="0")

    ahora = timezone.now()
    Trajectory.objects.create(
        camera=cam, started_at=ahora - timedelta(minutes=10), ended_at=ahora - timedelta(minutes=9),
        track_id=1, points=[[10, 20]], duration=60.0)
    Trajectory.objects.create(
        camera=cam, started_at=ahora - timedelta(minutes=60), ended_at=ahora - timedelta(minutes=59),
        track_id=2, points=[[30, 40]], duration=60.0)

    r = api_client.get(f"/api/camaras/{cam.pk}/trayectorias/")

    assert r.status_code == 200
    assert len(r.data["recorridos"]) == 2


@pytest.mark.django_db
def test_trayectorias_minutos_limite_300(api_client):
    from tenancy.models import Plan
    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    a = Business.objects.create(name="A", kind="retail", plan=plan)
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    api_client.force_authenticate(ana)

    cam = Camera.objects.create(business=a, name="Cam", source="0")

    ahora = timezone.now()
    for i in range(350):
        Trajectory.objects.create(
            camera=cam, started_at=ahora - timedelta(minutes=i), ended_at=ahora - timedelta(minutes=i) + timedelta(seconds=10),
            track_id=i, points=[[i, i]], duration=10.0)

    r = api_client.get(f"/api/camaras/{cam.pk}/trayectorias/?minutos=1000")

    assert r.status_code == 200
    assert len(r.data["recorridos"]) == 300


@pytest.mark.django_db
def test_trayectorias_minutos_invalido_ignora_filtro(api_client):
    from tenancy.models import Plan
    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    a = Business.objects.create(name="A", kind="retail", plan=plan)
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    api_client.force_authenticate(ana)

    cam = Camera.objects.create(business=a, name="Cam", source="0")

    ahora = timezone.now()
    Trajectory.objects.create(
        camera=cam, started_at=ahora - timedelta(minutes=10), ended_at=ahora - timedelta(minutes=9),
        track_id=1, points=[[10, 20]], duration=60.0)

    r = api_client.get(f"/api/camaras/{cam.pk}/trayectorias/?minutos=no-es-numero")

    assert r.status_code == 200
    assert len(r.data["recorridos"]) == 1


@pytest.mark.django_db
def test_trayectorias_segundos_filtra_por_ended_at(api_client):
    from tenancy.models import Plan
    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    a = Business.objects.create(name="A", kind="retail", plan=plan)
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    api_client.force_authenticate(ana)

    cam = Camera.objects.create(business=a, name="Cam", source="0")

    ahora = timezone.now()
    Trajectory.objects.create(
        camera=cam, started_at=ahora - timedelta(minutes=10), ended_at=ahora - timedelta(minutes=10) + timedelta(seconds=30),
        track_id=1, points=[[10, 20], [12, 22]], duration=30.0)
    Trajectory.objects.create(
        camera=cam, started_at=ahora - timedelta(minutes=60), ended_at=ahora - timedelta(minutes=60) + timedelta(seconds=30),
        track_id=2, points=[[30, 40], [32, 42]], duration=30.0)

    r = api_client.get(f"/api/camaras/{cam.pk}/trayectorias/?segundos=900")

    assert r.status_code == 200
    assert len(r.data["recorridos"]) == 1
    assert r.data["recorridos"][0]["track_id"] == 1
    assert "ended_at" in r.data["recorridos"][0]


@pytest.mark.django_db
def test_trayectorias_segundos_ignora_minutos(api_client):
    from tenancy.models import Plan
    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    a = Business.objects.create(name="A", kind="retail", plan=plan)
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    api_client.force_authenticate(ana)

    cam = Camera.objects.create(business=a, name="Cam", source="0")

    ahora = timezone.now()
    Trajectory.objects.create(
        camera=cam, started_at=ahora - timedelta(minutes=10), ended_at=ahora - timedelta(minutes=10) + timedelta(seconds=30),
        track_id=1, points=[[10, 20]], duration=30.0)
    Trajectory.objects.create(
        camera=cam, started_at=ahora - timedelta(minutes=60), ended_at=ahora - timedelta(minutes=60) + timedelta(seconds=30),
        track_id=2, points=[[30, 40]], duration=30.0)

    r = api_client.get(f"/api/camaras/{cam.pk}/trayectorias/?segundos=900&minutos=1000")

    assert r.status_code == 200
    assert len(r.data["recorridos"]) == 1
    assert r.data["recorridos"][0]["track_id"] == 1


@pytest.mark.django_db
def test_trayectorias_puntos_recorta_points(api_client):
    from tenancy.models import Plan
    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    a = Business.objects.create(name="A", kind="retail", plan=plan)
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    api_client.force_authenticate(ana)

    cam = Camera.objects.create(business=a, name="Cam", source="0")

    ahora = timezone.now()
    Trajectory.objects.create(
        camera=cam, started_at=ahora - timedelta(minutes=10), ended_at=ahora - timedelta(minutes=9),
        track_id=1, points=[[i, i] for i in range(20)], duration=60.0)

    r = api_client.get(f"/api/camaras/{cam.pk}/trayectorias/?puntos=6")

    assert r.status_code == 200
    assert len(r.data["recorridos"]) == 1
    assert len(r.data["recorridos"][0]["points"]) == 6
    assert r.data["recorridos"][0]["points"] == [[14, 14], [15, 15], [16, 16], [17, 17], [18, 18], [19, 19]]


@pytest.mark.django_db
def test_trayectorias_puntos_invalido_ignora(api_client):
    from tenancy.models import Plan
    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    a = Business.objects.create(name="A", kind="retail", plan=plan)
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    api_client.force_authenticate(ana)

    cam = Camera.objects.create(business=a, name="Cam", source="0")

    ahora = timezone.now()
    Trajectory.objects.create(
        camera=cam, started_at=ahora - timedelta(minutes=10), ended_at=ahora - timedelta(minutes=9),
        track_id=1, points=[[i, i] for i in range(10)], duration=60.0)

    r = api_client.get(f"/api/camaras/{cam.pk}/trayectorias/?puntos=no-es-numero")

    assert r.status_code == 200
    assert len(r.data["recorridos"]) == 1
    assert len(r.data["recorridos"][0]["points"]) == 10