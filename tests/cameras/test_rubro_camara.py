"""El detalle de una cámara trae el rubro de su negocio, para que el editor de
zonas pueda proponer las zonas de ese negocio.

Va aquí y no en un endpoint nuevo porque el editor ya pide este objeto al abrir.
"""
import pytest


@pytest.mark.django_db
def test_el_detalle_de_la_camara_trae_las_zonas_sugeridas(client_demo, camara_demo):
    r = client_demo.get(f"/api/camaras/{camara_demo.pk}/")

    assert r.status_code == 200
    nombres = [z["name"] for z in r.data["rubro"]["zonas"]]
    assert "Mesas" in nombres          # el negocio de camara_demo es kind="cafe"
    assert all("kind" in z for z in r.data["rubro"]["zonas"])


@pytest.mark.django_db
def test_las_zonas_sugeridas_cambian_con_el_rubro(client_demo, camara_demo):
    camara_demo.business.kind = "retail"
    camara_demo.business.save(update_fields=["kind"])

    r = client_demo.get(f"/api/camaras/{camara_demo.pk}/")

    nombres = [z["name"] for z in r.data["rubro"]["zonas"]]
    assert "Cajas" in nombres
    assert "Mesas" not in nombres


@pytest.mark.django_db
def test_el_listado_de_camaras_no_repite_el_rubro_en_cada_fila(client_demo, camara_demo):
    # El rubro es del negocio, no de la cámara: repetirlo N veces es peso muerto,
    # y el listado no lo usa.
    r = client_demo.get(f"/api/camaras/?business={camara_demo.business.pk}")

    assert "rubro" not in r.data[0]


@pytest.mark.django_db
def test_guardar_una_zona_con_el_tipo_sugerido(client_demo, camara_demo):
    r = client_demo.post(
        f"/api/camaras/{camara_demo.pk}/zonas/",
        {"name": "Mesas", "kind": "general",
         "polygon": [[0, 0], [10, 0], [10, 10]]}, format="json")

    assert r.status_code == 201
    assert r.data["kind"] == "general"


@pytest.mark.django_db
def test_una_camara_ajena_sigue_prohibida(client_sin_negocio, camara_demo):
    r = client_sin_negocio.get(f"/api/camaras/{camara_demo.pk}/")

    assert r.status_code in (403, 404)
