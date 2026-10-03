import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from cameras.ingesta import asegurar_h264, descargar_url, destino_para, guardar_subida


def test_destino_sanea_el_nombre(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    ruta = destino_para("../../etc/passwd.mp4")
    assert ruta.parent == tmp_path / "subidas"
    assert ".." not in ruta.name


def test_destino_no_pisa_un_archivo_existente(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    (tmp_path / "subidas").mkdir()
    (tmp_path / "subidas" / "clip.mp4").write_bytes(b"x")
    assert destino_para("clip.mp4").name != "clip.mp4"


def test_guardar_subida_escribe_el_contenido(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    archivo = SimpleUploadedFile("clip.mp4", b"avc1-contenido", content_type="video/mp4")
    ruta = guardar_subida(archivo, archivo.name)
    assert ruta.read_bytes() == b"avc1-contenido"


def test_descargar_url_usa_el_descargador_inyectado(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    llamadas = []

    def falso(url, plantilla_salida):
        llamadas.append((url, plantilla_salida))
        salida = tmp_path / "subidas" / "video.mp4"
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_bytes(b"avc1")
        return salida

    ruta = descargar_url("https://youtu.be/abc", descargador=falso)
    assert ruta.read_bytes() == b"avc1"
    assert llamadas[0][0] == "https://youtu.be/abc"


def test_asegurar_h264_deja_pasar_un_avc1(tmp_path):
    ruta = tmp_path / "ok.mp4"
    ruta.write_bytes(b"....avc1....")
    assert asegurar_h264(ruta) == ruta


def test_asegurar_h264_rechaza_lo_que_no_puede_convertir(tmp_path):
    ruta = tmp_path / "malo.mp4"
    ruta.write_bytes(b"no soy un video")
    with pytest.raises(ValueError, match="H.264"):
        asegurar_h264(ruta)


@pytest.fixture
def negocio_con_dueno():
    from django.contrib.auth.models import User

    from tenancy.models import Business, Plan, Profile

    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    business = Business.objects.create(name="A", kind="cafe", plan=plan)
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=business)
    return business, ana


@pytest.mark.django_db
def test_subir_video_crea_la_camara(api_client, negocio_con_dueno, settings, tmp_path):
    business, ana = negocio_con_dueno
    settings.MEDIA_ROOT = tmp_path
    settings.VIDEO_ROOTS = [str(tmp_path)]
    api_client.force_authenticate(ana)
    archivo = SimpleUploadedFile("pasillo.mp4", b"....avc1....", content_type="video/mp4")

    r = api_client.post("/api/camaras/subir/",
                        {"business": business.pk, "name": "Pasillo", "archivo": archivo},
                        format="multipart")

    assert r.status_code == 201, r.data
    assert r.data["source"].endswith("pasillo.mp4")


@pytest.mark.django_db
def test_subir_sin_archivo_ni_url_lo_dice(api_client, negocio_con_dueno):
    business, ana = negocio_con_dueno
    api_client.force_authenticate(ana)

    r = api_client.post("/api/camaras/subir/",
                        {"business": business.pk, "name": "X"}, format="multipart")

    assert r.status_code == 400
    assert "archivo" in str(r.data).lower()
