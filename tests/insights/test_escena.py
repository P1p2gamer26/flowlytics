import json

import pytest

from insights.client import FakeLlmClient
from insights.escena import describir_frame


def test_describir_frame_devuelve_descripcion_y_contexto():
    llm = FakeLlmClient(canned=json.dumps(
        {"descripcion": "Pasillo central de un supermercado, con cajas al fondo.",
         "contexto": "pasillo"}))
    resultado = describir_frame(b"jpeg-falso", llm)
    assert resultado["descripcion"].startswith("Pasillo central")
    assert resultado["contexto"] == "pasillo"


def test_un_contexto_inventado_cae_en_general():
    llm = FakeLlmClient(canned=json.dumps(
        {"descripcion": "Un pulpo tocando el piano.", "contexto": "acuario"}))
    assert describir_frame(b"jpeg-falso", llm)["contexto"] == "general"


def test_una_respuesta_que_no_es_json_no_rompe_la_carga():
    llm = FakeLlmClient(canned="lo siento, no puedo")
    resultado = describir_frame(b"jpeg-falso", llm)
    assert resultado["descripcion"] == ""
    assert resultado["contexto"] == "general"


@pytest.mark.django_db
def test_describir_guarda_la_frase_en_la_camara(client_demo, camara_demo, monkeypatch, settings):
    settings.ANTHROPIC_API_KEY = "sk-test"
    monkeypatch.setattr("cameras.api._cliente_llm", lambda: FakeLlmClient(
        canned=json.dumps({"descripcion": "Caja de un supermercado.",
                           "contexto": "counter"})))
    monkeypatch.setattr("cameras.api._primer_frame_jpeg", lambda camera: b"jpeg")

    r = client_demo.post(f"/api/camaras/{camara_demo.pk}/describir/")
    assert r.status_code == 200
    assert r.data["contexto"] == "counter"

    camara_demo.refresh_from_db()
    assert camara_demo.descripcion == "Caja de un supermercado."
    assert camara_demo.contexto == "counter"


@pytest.mark.django_db
def test_sin_api_key_el_endpoint_lo_dice_sin_romperse(client_demo, camara_demo, settings):
    settings.ANTHROPIC_API_KEY = ""
    r = client_demo.post(f"/api/camaras/{camara_demo.pk}/describir/")
    assert r.status_code == 503
    assert "descripción" in str(r.data).lower() or "clave" in str(r.data).lower()
