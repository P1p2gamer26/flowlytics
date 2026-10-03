import pytest


@pytest.mark.django_db
def test_el_shell_pide_login(client):
    r = client.get("/")
    assert r.status_code == 302
    assert "/login" in r.url


@pytest.mark.django_db
def test_cualquier_ruta_del_front_devuelve_el_shell(client_demo_django):
    for ruta in ["/", "/camaras/", "/camaras/1/", "/subir/"]:
        assert client_demo_django.get(ruta).status_code == 200


@pytest.mark.django_db
def test_el_catch_all_no_se_come_la_api_ni_el_admin(client_demo_django):
    assert client_demo_django.get("/api/negocio-actual/").status_code == 200
    assert client_demo_django.get("/admin/").status_code in (200, 302)
