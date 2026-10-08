import json
import time

import pytest
from django.contrib.auth.models import User

from cameras.models import Camera
from tenancy.models import Business, Profile
from vision.estelas import EstelasVivas


def test_recorta_a_los_ultimos_puntos():
    e = EstelasVivas(max_puntos=6, max_edad_s=3.0)
    for i in range(10):
        e.observar([(1, (i * 10.4, 5.6))], t=i * 0.1)
    [r] = e.recientes(t=1.0)
    assert r["track_id"] == 1
    assert len(r["points"]) == 6
    assert list(r["points"][-1]) == [94, 6]


def test_purga_tracks_viejos_e_ignora_un_solo_punto():
    e = EstelasVivas(max_puntos=6, max_edad_s=3.0)
    e.observar([(1, (0, 0)), (2, (5, 5))], t=0.0)
    e.observar([(1, (1, 1))], t=0.5)
    e.observar([(3, (9, 9))], t=4.0)  # el 3 solo tiene un punto
    assert e.recientes(t=4.0) == []    # 1 y 2 caducaron, 3 no tiene estela
    assert 1 not in e._tracks and 2 not in e._tracks


@pytest.fixture
def mundo(db, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    (tmp_path / "en_vivo").mkdir()
    biz = Business.objects.create(name="B", kind="cafe")
    cam = Camera.objects.create(business=biz, name="c", source="0")
    owner = User.objects.create_user("o", password="x")
    Profile.objects.create(user=owner, role="owner", business=biz)
    return dict(cam=cam, owner=owner, dir=tmp_path / "en_vivo")


def _escribir(mundo, t):
    datos = {"recorridos": [{"track_id": 7, "points": [[1, 2], [3, 4]]}], "t": t}
    (mundo["dir"] / f"{mundo['cam'].pk}_estelas.json").write_text(json.dumps(datos))


@pytest.mark.django_db
def test_vista_estelas(api_client, mundo):
    api_client.force_authenticate(mundo["owner"])
    url = f"/api/camaras/{mundo['cam'].pk}/estelas/"

    assert api_client.get(url).json() == {"recorridos": []}          # sin archivo

    _escribir(mundo, time.time())
    r = api_client.get(url)
    assert r.json()["recorridos"][0]["track_id"] == 7
    assert r["Cache-Control"] == "no-store"

    _escribir(mundo, time.time() - 60)                                 # viejo
    assert api_client.get(url).json() == {"recorridos": []}


@pytest.mark.django_db
def test_vista_estelas_de_otro_negocio_es_403(api_client, mundo):
    ajeno = User.objects.create_user("x", password="x")
    otro = Business.objects.create(name="Otro", kind="cafe")
    Profile.objects.create(user=ajeno, role="owner", business=otro)
    api_client.force_authenticate(ajeno)
    assert api_client.get(f"/api/camaras/{mundo['cam'].pk}/estelas/").status_code == 403
