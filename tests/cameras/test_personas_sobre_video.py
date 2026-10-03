"""Los recuadros sobre las personas y la marca de personal.

El recorrido se guarda al analizar y el front lo pinta encima del video; marcar a
alguien es etiquetar un `track_id` de ESA corrida, no reconocer una cara.
"""
import pytest

from cameras.models import MarcaPersona, Recorrido


@pytest.mark.django_db
def test_permanencia_de_la_primera_a_la_ultima_vez_que_se_le_vio(camara_demo):
    r = Recorrido.objects.create(camera=camara_demo, pistas=[
        {"t": 10.0, "cajas": [{"id": 7, "xyxy": [0, 0, 1, 1]}]},
        {"t": 70.0, "cajas": [{"id": 7, "xyxy": [0, 0, 1, 1]},
                              {"id": 8, "xyxy": [0, 0, 1, 1]}]},
    ])
    assert r.permanencias() == {7: 60.0, 8: 0.0}


@pytest.mark.django_db
def test_una_camara_tiene_un_solo_recorrido(camara_demo):
    """Reanalizar reemplaza; no deja dos verdades sobre el mismo video."""
    Recorrido.objects.update_or_create(camera=camara_demo,
                                       defaults={"pistas": [{"t": 0, "cajas": []}]})
    Recorrido.objects.update_or_create(camera=camara_demo, defaults={"pistas": []})
    assert Recorrido.objects.filter(camera=camara_demo).count() == 1


@pytest.mark.django_db
def test_el_endpoint_devuelve_pistas_permanencias_y_personal(client_demo, camara_demo):
    Recorrido.objects.create(camera=camara_demo, pistas=[
        {"t": 0.0, "cajas": [{"id": 4, "xyxy": [1, 2, 3, 4]}]},
        {"t": 30.0, "cajas": [{"id": 4, "xyxy": [1, 2, 3, 4]}]},
    ])
    r = client_demo.get(f"/api/camaras/{camara_demo.pk}/recorrido/")
    assert r.status_code == 200
    assert r.data["analizado"] is True
    assert r.data["permanencias"]["4"] == 30.0
    assert r.data["personal"] == []


@pytest.mark.django_db
def test_sin_analisis_no_es_un_error(client_demo, camara_demo):
    """Una cámara que nadie ha analizado no tiene personas, y eso no es un fallo."""
    r = client_demo.get(f"/api/camaras/{camara_demo.pk}/recorrido/")
    assert r.status_code == 200
    assert r.data["analizado"] is False
    assert r.data["pistas"] == []


@pytest.mark.django_db
def test_marcar_y_desmarcar_a_alguien_como_personal(client_demo, camara_demo):
    url = f"/api/camaras/{camara_demo.pk}/personal/"
    assert client_demo.post(url, {"track_id": 4, "es_personal": True},
                            format="json").data["personal"] == [4]
    assert client_demo.post(url, {"track_id": 4, "es_personal": False},
                            format="json").data["personal"] == []
    assert MarcaPersona.objects.filter(camera=camara_demo, track_id=4).count() == 1


@pytest.mark.django_db
def test_sin_track_id_lo_dice_en_vez_de_reventar(client_demo, camara_demo):
    r = client_demo.post(f"/api/camaras/{camara_demo.pk}/personal/", {}, format="json")
    assert r.status_code == 400


@pytest.mark.django_db
def test_no_se_puede_marcar_en_la_camara_de_otro(client_demo, db):
    from cameras.models import Camera
    from tenancy.models import Business

    ajena = Camera.objects.create(
        business=Business.objects.create(name="Otra", kind="cafe"),
        name="Ajena", source="0")
    r = client_demo.post(f"/api/camaras/{ajena.pk}/personal/",
                         {"track_id": 1, "es_personal": True}, format="json")
    assert r.status_code == 403
