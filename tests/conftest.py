import pytest


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def camara_demo(db, settings, tmp_path):
    """Cámara de archivo, con un video real y legible y una zona dibujada,
    lista para pruebas de endpoints que necesitan leer un frame o analizar."""
    from django.contrib.auth.models import User

    from cameras.models import Camera, Zone
    from tenancy.models import Business, Profile
    from tests.cameras.test_vista import generar_video

    settings.VIDEO_ROOTS = [str(tmp_path)]
    video = tmp_path / "demo.mp4"
    generar_video(video)
    business = Business.objects.create(name="Demo", kind="cafe")
    dueno = User.objects.create_user("demo", password="x")
    Profile.objects.create(user=dueno, role="owner", business=business)
    camera = Camera.objects.create(business=business, name="Demo",
                                   source=f"file://{video}")
    camera.dueno = dueno
    Zone.objects.create(camera=camera, name="zona", kind="general",
                        polygon=[[0, 0], [10, 0], [10, 10], [0, 10]])
    return camera


@pytest.fixture
def client_demo(api_client, camara_demo):
    """Cliente autenticado como el dueño de `camara_demo`."""
    api_client.force_authenticate(camara_demo.dueno)
    return api_client


@pytest.fixture
def client_demo_django(camara_demo):
    """Cliente Django (no DRF) autenticado por sesión como el dueño de `camara_demo`."""
    from django.test import Client

    client = Client()
    client.force_login(camara_demo.dueno)
    return client


@pytest.fixture
def client_sin_negocio(api_client, db):
    """Cliente autenticado como un usuario sin perfil ni negocio asignado."""
    from django.contrib.auth.models import User

    huerfano = User.objects.create_user("sin-negocio", password="x")
    api_client.force_authenticate(huerfano)
    return api_client


@pytest.fixture
def ventana_demo(camara_demo):
    """Un `MetricWindow` ya calculado para `camara_demo`."""
    from django.utils import timezone

    from analytics.models import MetricWindow

    ahora = timezone.now()
    return MetricWindow.objects.create(
        camera=camara_demo, zone_name="zona", zone_kind="general",
        started_at=ahora, ended_at=ahora, occupancy_avg=1.0,
        occupancy_max=1, dwell_seconds=5.0, unique_visitors=1)
