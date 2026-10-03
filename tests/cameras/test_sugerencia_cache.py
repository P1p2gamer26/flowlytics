"""La segunda apertura de la misma cámara no vuelve a analizar el video."""
import pytest
from django.contrib.auth.models import User
from django.core.cache import cache

from cameras.models import Camera
from tenancy.models import Business, Profile

from .test_vista import generar_video


@pytest.fixture
def mundo(db):
    biz = Business.objects.create(name="A", kind="cafe")
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=biz)
    return dict(biz=biz, ana=ana)


@pytest.fixture(autouse=True)
def limpia_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def camara(mundo, settings, tmp_path):
    settings.VIDEO_ROOTS = [str(tmp_path)]
    video = tmp_path / "v.mp4"
    # Pocos frames: generar_video pinta cada uno con i*40 en uint8 y a partir
    # del séptimo se desborda.
    generar_video(video, frames=6, ancho=64, alto=48)
    return Camera.objects.create(business=mundo["biz"], name="V",
                                 source=f"file://{video}")


@pytest.fixture
def analisis(monkeypatch):
    """Cuenta cuántas veces se analiza de verdad el video.

    Se parchea el cálculo del polígono, que es lo último del análisis: si no se
    llama, es que la respuesta salió de la caché.
    """
    contador = {"n": 0}

    def falso(puntos, frame_wh, *a, **k):
        contador["n"] += 1
        return [[0, 0], [10, 0], [10, 10]]

    monkeypatch.setattr("vision.core.sugerencia.poligono_sugerido", falso)
    return contador


@pytest.mark.django_db
def test_la_segunda_llamada_no_reanaliza(api_client, mundo, camara, analisis):
    api_client.force_authenticate(mundo["ana"])
    url = f"/api/camaras/{camara.pk}/sugerir_zona/"

    primera = api_client.get(url)
    tras_primera = analisis["n"]
    segunda = api_client.get(url)

    assert primera.status_code == 200
    assert segunda.status_code == 200
    assert primera.json()["cacheado"] is False
    assert segunda.json()["cacheado"] is True
    assert analisis["n"] == tras_primera, "volvió a analizar el video"
    assert segunda.json()["polygon"] == primera.json()["polygon"]


@pytest.mark.django_db
def test_refrescar_ignora_la_cache(api_client, mundo, camara, analisis):
    api_client.force_authenticate(mundo["ana"])
    url = f"/api/camaras/{camara.pk}/sugerir_zona/"

    api_client.get(url)
    tras_primera = analisis["n"]
    r = api_client.get(url + "?refrescar=1")

    assert r.status_code == 200
    assert r.json()["cacheado"] is False
    assert analisis["n"] > tras_primera


@pytest.mark.django_db
def test_cambiar_el_video_invalida_la_cache(api_client, mundo, camara, analisis,
                                            tmp_path):
    api_client.force_authenticate(mundo["ana"])
    url = f"/api/camaras/{camara.pk}/sugerir_zona/"

    api_client.get(url)
    tras_primera = analisis["n"]
    # mismo nombre de archivo, contenido nuevo: la sugerencia vieja ya no vale
    generar_video(tmp_path / "v.mp4", frames=7, ancho=64, alto=48)

    r = api_client.get(url)

    assert r.status_code == 200
    assert r.json()["cacheado"] is False
    assert analisis["n"] > tras_primera
