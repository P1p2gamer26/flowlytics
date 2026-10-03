import pytest
from rest_framework.test import APIClient
from cameras.models import MarcaPersona, Recorrido

@pytest.mark.django_db
def test_marca_se_guarda_y_se_lee_en_el_recorrido(client_demo, camara_demo):
    Recorrido.objects.create(camera=camara_demo, pistas=[
        {"t": 0, "cajas": [{"id": 4, "xyxy": [1, 2, 3, 4]}]},
    ])
    # Marcar como personal
    resp = client_demo.post(
        f"/api/camaras/{camara_demo.pk}/personal/",
        {"track_id": 4, "es_personal": True}, format="json")
    assert resp.status_code == 200
    assert resp.data["personal"] == [4]

    # Leer recorrido: debe incluir la marca
    recorrido_resp = client_demo.get(
        f"/api/camaras/{camara_demo.pk}/recorrido/")
    assert recorrido_resp.status_code == 200
    assert recorrido_resp.data["personal"] == [4]
    assert recorrido_resp.data["pistas"][0]["cajas"][0]["id"] == 4


@pytest.mark.django_db
def test_contraste_visual_cliente_vs_staff(client_demo, camara_demo):
    Recorrido.objects.create(camera=camara_demo, pistas=[
        {"t": 0, "cajas": [{"id": 10, "xyxy": [10, 20, 30, 40]}]},
        {"t": 60, "cajas": [{"id": 10, "xyxy": [10, 20, 30, 40]}]},
    ])
    # Marcar como personal
    client_demo.post(f"/api/camaras/{camara_demo.pk}/personal/",
                     {"track_id": 10, "es_personal": True}, format="json")
    resp = client_demo.get(f"/api/camaras/{camara_demo.pk}/recorrido/")
    assert resp.data["personal"] == [10]
    assert resp.data["permanencias"].get("10") == 60.0


@pytest.mark.django_db
def test_marca_persiste_tras_nuevo_analisis(client_demo, camara_demo):
    """La marca persiste aunque se cree un nuevo Recorrido sobre la misma cámara."""
    Recorrido.objects.create(camera=camara_demo, pistas=[
        {"t": 1, "cajas": [{"id": 7, "xyxy": [5, 6, 7, 8]}]},
    ])
    # Crear la marca a través del endpoint
    resp = client_demo.post(
        f"/api/camaras/{camara_demo.pk}/personal/",
        {"track_id": 4, "es_personal": True}, format="json")
    assert resp.status_code == 200
    assert resp.data["personal"] == [4]

    # Nuevo análisis (reemplaza Recorrido en esta cámara)
    Recorrido.objects.filter(camera=camara_demo).delete()
    Recorrido.objects.create(camera=camara_demo, pistas=[
        {"t": 2, "cajas": [{"id": 9, "xyxy": [9, 9, 9, 9]}]},
    ])
    recorrido_resp = client_demo.get(
        f"/api/camaras/{camara_demo.pk}/recorrido/")
    assert recorrido_resp.status_code == 200
    assert recorrido_resp.data["personal"] == [4]
