import pytest


@pytest.mark.django_db
def test_devuelve_el_negocio_del_usuario(client_demo, camara_demo):
    r = client_demo.get("/api/negocio-actual/")
    assert r.status_code == 200
    assert r.data["business_id"] == camara_demo.business.pk


@pytest.mark.django_db
def test_sin_negocio_devuelve_404(client_sin_negocio):
    assert client_sin_negocio.get("/api/negocio-actual/").status_code == 404


@pytest.mark.django_db
def test_lista_los_negocios_visibles(client_demo, camara_demo):
    r = client_demo.get("/api/negocio-actual/")
    assert [n["id"] for n in r.data["negocios"]] == [camara_demo.business.pk]
