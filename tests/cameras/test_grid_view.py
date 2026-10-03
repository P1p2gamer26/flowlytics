import pytest

from cameras.models import Camera, CameraHealth, Recorrido

@pytest.mark.django_db
def test_una_camara_analizada_y_viva_muestra_gente_ahora(client_demo, camara_demo):
    Recorrido.objects.create(camera=camara_demo, pistas=[
        {"t": 0.0, "cajas": [{"id": 1, "xyxy": [0, 0, 1, 1]}]},
        {"t": 1.0, "cajas": [{"id": 1, "xyxy": [0, 0, 1, 1]},
                             {"id": 2, "xyxy": [0, 0, 1, 1]}]},
    ])
    CameraHealth.latir(camara_demo, frames=100, reconexiones=0)

    r = client_demo.get(f"/api/camaras/grid/?business={camara_demo.business_id}")

    assert r.status_code == 200
    fila = r.data[0]
    assert fila["id"] == camara_demo.pk
    assert fila["gente_ahora"] == 2
    assert fila["viva"] is True
    assert fila["analizado"] is True

@pytest.mark.django_db
def test_una_camara_sin_analizar_no_inventa_gente(client_demo, camara_demo):
    r = client_demo.get(f"/api/camaras/grid/?business={camara_demo.business_id}")

    fila = r.data[0]
    assert fila["analizado"] is False
    assert fila["gente_ahora"] == 0

@pytest.mark.django_db
def test_una_camara_sin_latido_reciente_sale_sin_senal(client_demo, camara_demo):
    from datetime import timedelta

    from django.utils import timezone

    salud = CameraHealth.latir(camara_demo, frames=10, reconexiones=0)
    salud.ultimo_latido = timezone.now() - timedelta(seconds=999)
    salud.save()

    r = client_demo.get(f"/api/camaras/grid/?business={camara_demo.business_id}")

    assert r.data[0]["viva"] is False

@pytest.mark.django_db
def test_una_camara_sin_salud_todavia_no_es_un_error(client_demo, camara_demo):
    """Recien creada, nadie la ha corrido: no tiene CameraHealth. No es 500."""
    r = client_demo.get(f"/api/camaras/grid/?business={camara_demo.business_id}")

    assert r.status_code == 200
    assert r.data[0]["viva"] is False

@pytest.mark.django_db
def test_no_se_ve_el_grid_de_otro_negocio(api_client):
    from tenancy.models import Business, Profile
    from django.contrib.auth.models import User

    a = Business.objects.create(name="A", kind="cafe")
    b = Business.objects.create(name="B", kind="retail")
    Camera.objects.create(business=b, name="cb", source="0")
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    api_client.force_authenticate(ana)

    r = api_client.get(f"/api/camaras/grid/?business={b.pk}")

    assert r.status_code == 403
