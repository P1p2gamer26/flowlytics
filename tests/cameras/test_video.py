"""La vista sirve el archivo de video al editor, sin dejar leer el disco entero."""
import pytest
from django.contrib.auth.models import User

from cameras.models import Camera
from tenancy.models import Business, Profile

from .test_vista import generar_video


@pytest.fixture
def mundo(db):
    biz = Business.objects.create(name="A", kind="cafe")
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=biz)
    return dict(biz=biz, ana=ana)


@pytest.fixture
def raiz(settings, tmp_path):
    settings.VIDEO_ROOTS = [str(tmp_path)]
    return tmp_path


@pytest.mark.django_db
def test_sirve_el_archivo_de_video(api_client, mundo, raiz):
    video = raiz / "tienda.mp4"
    generar_video(video)
    cam = Camera.objects.create(business=mundo["biz"], name="T",
                                source=f"file://{video}")
    api_client.force_authenticate(mundo["ana"])

    r = api_client.get(f"/api/camaras/{cam.pk}/video/")

    assert r.status_code == 200
    assert r["Content-Type"] == "video/mp4"
    assert b"".join(r.streaming_content) == video.read_bytes()


@pytest.mark.django_db
def test_rechaza_un_archivo_fuera_de_las_raices_permitidas(api_client, mundo, raiz,
                                                           tmp_path_factory):
    fuera = tmp_path_factory.mktemp("otro") / "secreto.mp4"
    generar_video(fuera)
    cam = Camera.objects.create(business=mundo["biz"], name="Fuga",
                                source=f"file://{fuera}")
    api_client.force_authenticate(mundo["ana"])

    r = api_client.get(f"/api/camaras/{cam.pk}/video/")

    assert r.status_code == 403


@pytest.mark.django_db
def test_rechaza_travesia_con_dos_puntos(api_client, mundo, raiz):
    cam = Camera.objects.create(business=mundo["biz"], name="Traversal",
                                source=f"file://{raiz}/../../etc/passwd")
    api_client.force_authenticate(mundo["ana"])

    r = api_client.get(f"/api/camaras/{cam.pk}/video/")

    assert r.status_code in (403, 404)


@pytest.mark.django_db
def test_rechaza_rtsp(api_client, mundo, raiz):
    cam = Camera.objects.create(business=mundo["biz"], name="RTSP",
                                source="rtsp://10.0.0.5:554/stream")
    api_client.force_authenticate(mundo["ana"])

    assert api_client.get(f"/api/camaras/{cam.pk}/video/").status_code == 400


@pytest.mark.django_db
def test_video_de_camara_ajena_es_403(api_client, mundo, raiz):
    otra = Business.objects.create(name="B", kind="retail")
    cam = Camera.objects.create(business=otra, name="Ajena", source="0")
    api_client.force_authenticate(mundo["ana"])

    assert api_client.get(f"/api/camaras/{cam.pk}/video/").status_code in (403, 404)
