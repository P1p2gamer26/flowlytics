import json
import os
import time
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.utils import timezone

from cameras.models import Camera
from tenancy.models import Business, Profile


@pytest.fixture
def world(db, settings):
    # Configurar MEDIA_ROOT temporal
    media_root = settings.MEDIA_ROOT
    en_vivo_dir = Path(media_root) / "en_vivo"
    en_vivo_dir.mkdir(parents=True, exist_ok=True)

    biz = Business.objects.create(name="Test Biz", kind="cafe")
    cam = Camera.objects.create(business=biz, name="cam1", source="0")
    owner = User.objects.create_user("owner", password="x")
    Profile.objects.create(user=owner, role="owner", business=biz)

    yield dict(biz=biz, cam=cam, owner=owner, en_vivo_dir=en_vivo_dir)

    # Cleanup
    for f in en_vivo_dir.glob("*"):
        f.unlink(missing_ok=True)


@pytest.mark.django_db
def test_camara_ahora_404_si_no_existe_archivo(api_client, world, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)  # no mirar el media/ real: puede tener ese jpg
    owner = world["owner"]
    cam = world["cam"]
    api_client.force_authenticate(owner)

    r = api_client.get(f"/api/camaras/{cam.pk}/ahora/")
    assert r.status_code == 404


@pytest.mark.django_db
def test_camara_ahora_200_si_existe_jpg(api_client, world, settings):
    owner = world["owner"]
    cam = world["cam"]
    api_client.force_authenticate(owner)

    # Crear un JPEG temporal
    jpg_path = world["en_vivo_dir"] / f"{cam.pk}.jpg"
    jpg_path.write_bytes(b"fake jpeg data")

    r = api_client.get(f"/api/camaras/{cam.pk}/ahora/")
    assert r.status_code == 200
    assert r["Content-Type"] == "image/jpeg"
    assert r["Cache-Control"] == "no-store"


@pytest.mark.django_db
def test_camaras_grid_view_usa_json_fresco(api_client, world, settings):
    owner = world["owner"]
    biz = world["biz"]
    cam = world["cam"]
    api_client.force_authenticate(owner)

    # Crear JSON fresco con gente_ahora = 5
    json_path = world["en_vivo_dir"] / f"{cam.pk}.json"
    json_path.write_text(json.dumps({"personas": 5, "t": time.time()}))

    r = api_client.get("/api/camaras/grid/", {"business": biz.pk})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["gente_ahora"] == 5
    assert data[0]["viva"] is True


@pytest.mark.django_db
def test_camaras_grid_view_ignora_json_viejo(api_client, world, settings):
    owner = world["owner"]
    biz = world["biz"]
    cam = world["cam"]
    api_client.force_authenticate(owner)

    # Crear JSON viejo (> 30 s)
    json_path = world["en_vivo_dir"] / f"{cam.pk}.json"
    json_path.write_text(json.dumps({"personas": 99, "t": time.time() - 60}))

    r = api_client.get("/api/camaras/grid/", {"business": biz.pk})
    assert r.status_code == 200
    data = r.json()
    # Debe usar el valor por defecto (0) porque el JSON es viejo
    assert data[0]["gente_ahora"] == 0
    assert data[0]["viva"] is False


@pytest.mark.django_db
def test_camaras_en_vivo_view_usa_json_fresco(api_client, world, settings):
    owner = world["owner"]
    cam = world["cam"]
    api_client.force_authenticate(owner)

    # Crear JSON fresco
    json_path = world["en_vivo_dir"] / f"{cam.pk}.json"
    json_path.write_text(json.dumps({"personas": 3, "t": time.time()}))

    r = api_client.get("/api/camaras/en_vivo/")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["gente_ahora"] == 3
    assert data[0]["viva"] is True


@pytest.mark.django_db
def test_camaras_en_vivo_view_ignora_json_viejo(api_client, world, settings):
    owner = world["owner"]
    cam = world["cam"]
    api_client.force_authenticate(owner)

    # Crear JSON viejo
    json_path = world["en_vivo_dir"] / f"{cam.pk}.json"
    json_path.write_text(json.dumps({"personas": 99, "t": time.time() - 60}))

    r = api_client.get("/api/camaras/en_vivo/")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    # Sin Recorrido, gente_ahora debe ser 0
    assert data[0]["gente_ahora"] == 0
    assert data[0]["viva"] is False