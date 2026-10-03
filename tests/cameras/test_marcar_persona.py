import pytest


@pytest.mark.django_db
def test_el_recorrido_expone_rastros_con_el_pie_de_las_cajas(client_demo, camara_demo):
    from cameras.models import Recorrido

    Recorrido.objects.create(camera=camara_demo, pistas=[
        {"t": 0.0, "cajas": [{"id": 4, "xyxy": [10, 20, 50, 120]}]},
        {"t": 0.5, "cajas": [{"id": 4, "xyxy": [20, 20, 60, 130]}]},
    ])

    r = client_demo.get(f"/api/camaras/{camara_demo.pk}/recorrido/")

    assert r.status_code == 200
    assert r.data["rastros"] == [{"track_id": 4, "puntos": [
        {"t": 0.0, "xy": [30.0, 120.0]},
        {"t": 0.5, "xy": [40.0, 130.0]},
    ]}]


@pytest.mark.django_db
def test_una_camara_sin_analisis_expone_cero_rastros(client_demo, camara_demo):
    r = client_demo.get(f"/api/camaras/{camara_demo.pk}/recorrido/")
    assert r.data["rastros"] == []
