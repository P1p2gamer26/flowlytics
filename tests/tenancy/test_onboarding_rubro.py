"""Los primeros pasos nombran las zonas del rubro en vez de decir "una zona"."""
import pytest


@pytest.mark.django_db
def test_el_onboarding_nombra_las_zonas_del_rubro(client_demo_django, camara_demo):
    r = client_demo_django.get("/onboarding/")

    assert r.status_code == 200
    cuerpo = r.content.decode()
    assert "Mesas" in cuerpo          # negocio kind="cafe"
    assert "Barra" in cuerpo


@pytest.mark.django_db
def test_cambiar_el_rubro_cambia_lo_que_sugiere(client_demo_django, camara_demo):
    camara_demo.business.kind = "retail"
    camara_demo.business.save(update_fields=["kind"])

    cuerpo = client_demo_django.get("/onboarding/").content.decode()

    assert "Cajas" in cuerpo
    assert "Mesas" not in cuerpo
