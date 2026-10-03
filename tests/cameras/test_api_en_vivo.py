"""Pruebas del endpoint /api/camaras/en_vivo/."""
import pytest
from urllib.parse import urlparse, parse_qs

from cameras.models import Camera, CameraHealth, Recorrido, Zone
from tenancy.models import Business, Profile
from django.contrib.auth.models import User


@pytest.mark.django_db
def test_en_vivo_devuelve_camaras_de_negocios_visibles(api_client):
    from tenancy.models import Plan
    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    a = Business.objects.create(name="A", kind="retail", plan=plan)
    b = Business.objects.create(name="B", kind="cafe", plan=plan)
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    api_client.force_authenticate(ana)

    Camera.objects.create(business=a, name="Cam A", source="0")
    Camera.objects.create(business=b, name="Cam B", source="0")

    r = api_client.get("/api/camaras/en_vivo/")

    assert r.status_code == 200
    assert len(r.data) == 1
    assert r.data[0]["name"] == "Cam A"
    assert r.data[0]["negocio"] == "A"


@pytest.mark.django_db
def test_en_vivo_youtube_id_correcto(api_client):
    from tenancy.models import Plan
    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    a = Business.objects.create(name="A", kind="retail", plan=plan)
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    api_client.force_authenticate(ana)

    url = "https://www.youtube.com/watch?v=3o9aoRyrvAk"
    Camera.objects.create(business=a, name="YouTube", source=url)

    r = api_client.get("/api/camaras/en_vivo/")

    assert r.status_code == 200
    cam = r.data[0]
    assert cam["tipo"] == "youtube"
    assert cam["youtube_id"] == "3o9aoRyrvAk"


@pytest.mark.django_db
def test_en_vivo_youtu_be_id_correcto(api_client):
    from tenancy.models import Plan
    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    a = Business.objects.create(name="A", kind="retail", plan=plan)
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    api_client.force_authenticate(ana)

    url = "https://youtu.be/abc123XYZ"
    Camera.objects.create(business=a, name="YouTube short", source=url)

    r = api_client.get("/api/camaras/en_vivo/")

    assert r.status_code == 200
    cam = r.data[0]
    assert cam["tipo"] == "youtube"
    assert cam["youtube_id"] == "abc123XYZ"


@pytest.mark.django_db
def test_en_vivo_archivo_tiene_video_url(api_client, tmp_path, settings):
    from tenancy.models import Plan
    from tests.cameras.test_vista import generar_video

    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    a = Business.objects.create(name="A", kind="retail", plan=plan)
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    api_client.force_authenticate(ana)

    settings.VIDEO_ROOTS = [str(tmp_path)]
    video = tmp_path / "demo.mp4"
    generar_video(video)
    cam = Camera.objects.create(business=a, name="Video", source=f"file://{video}")

    r = api_client.get("/api/camaras/en_vivo/")

    assert r.status_code == 200
    data = r.data[0]
    assert data["tipo"] == "archivo"
    assert data["video"] == f"/api/camaras/{cam.pk}/video/"
    assert data["youtube_id"] is None


@pytest.mark.django_db
def test_en_vivo_stream_tipo_y_sin_video(api_client):
    from tenancy.models import Plan
    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    a = Business.objects.create(name="A", kind="retail", plan=plan)
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    api_client.force_authenticate(ana)

    Camera.objects.create(business=a, name="RTSP", source="rtsp://cam/stream")

    r = api_client.get("/api/camaras/en_vivo/")

    assert r.status_code == 200
    data = r.data[0]
    assert data["tipo"] == "stream"
    assert data["video"] is None
    assert data["youtube_id"] is None


@pytest.mark.django_db
def test_en_vivo_viva_y_gente_ahora(api_client):
    from tenancy.models import Plan
    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    a = Business.objects.create(name="A", kind="retail", plan=plan)
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    api_client.force_authenticate(ana)

    cam = Camera.objects.create(business=a, name="Viva", source="0")
    CameraHealth.latir(cam, frames=100, reconexiones=0)
    Recorrido.objects.create(camera=cam, pistas=[
        {"t": 0.0, "cajas": [{"id": 1, "xyxy": [0, 0, 1, 1]}]},
        {"t": 1.0, "cajas": [{"id": 1, "xyxy": [0, 0, 1, 1]}, {"id": 2, "xyxy": [0, 0, 1, 1]}]},
    ])

    r = api_client.get("/api/camaras/en_vivo/")

    assert r.status_code == 200
    data = r.data[0]
    assert data["viva"] is True
    assert data["gente_ahora"] == 2


@pytest.mark.django_db
def test_en_vivo_sin_salud_no_es_error(api_client):
    from tenancy.models import Plan
    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    a = Business.objects.create(name="A", kind="retail", plan=plan)
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    api_client.force_authenticate(ana)

    Camera.objects.create(business=a, name="Nueva", source="0")

    r = api_client.get("/api/camaras/en_vivo/")

    assert r.status_code == 200
    data = r.data[0]
    assert data["viva"] is False
    assert data["gente_ahora"] == 0


@pytest.mark.django_db
def test_en_vivo_zonas_incluidas(api_client):
    from tenancy.models import Plan
    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    a = Business.objects.create(name="A", kind="retail", plan=plan)
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    api_client.force_authenticate(ana)

    cam = Camera.objects.create(business=a, name="Con zonas", source="0")
    Zone.objects.create(camera=cam, name="Entrada", kind="entrada", polygon=[[0,0],[10,0],[10,10],[0,10]])
    Zone.objects.create(camera=cam, name="Caja", kind="counter", polygon=[[20,20],[30,20],[30,30],[20,30]])

    r = api_client.get("/api/camaras/en_vivo/")

    assert r.status_code == 200
    zonas = r.data[0]["zonas"]
    assert len(zonas) == 2
    assert zonas[0]["name"] == "Entrada"
    assert zonas[0]["kind"] == "entrada"
    assert zonas[0]["polygon"] == [[0,0],[10,0],[10,10],[0,10]]
    assert zonas[1]["name"] == "Caja"
    assert zonas[1]["kind"] == "counter"


@pytest.mark.django_db
def test_en_vivo_ancho_alto_desde_archivo_si_cero(api_client, tmp_path, settings):
    from tenancy.models import Plan
    from tests.cameras.test_vista import generar_video

    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    a = Business.objects.create(name="A", kind="retail", plan=plan)
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    api_client.force_authenticate(ana)

    settings.VIDEO_ROOTS = [str(tmp_path)]
    video = tmp_path / "demo.mp4"
    generar_video(video, ancho=320, alto=240)
    Camera.objects.create(business=a, name="Video", source=f"file://{video}", frame_w=0, frame_h=0)

    r = api_client.get("/api/camaras/en_vivo/")

    assert r.status_code == 200
    data = r.data[0]
    assert data["width"] == 320
    assert data["height"] == 240