"""Aislamiento multi-tenant: autenticados como dueña de A, atacamos cada endpoint
apuntando a recursos de B y exigimos que se niegue (403/404) y no filtre datos.

Cada endpoint que reciba un `business` o un objeto de un negocio DEBE aparecer aquí.
Si agregas un endpoint nuevo con datos de tenant, agrégale un caso a esta suite."""
import pytest
from django.contrib.auth.models import User

from cameras.models import Camera, CountingLine, Zone
from tenancy.models import Business, Invitation, Profile


@pytest.fixture
def dos_mundos(db):
    a = Business.objects.create(name="Alfa", kind="cafe")
    b = Business.objects.create(name="Beta", kind="retail")
    cam_a = Camera.objects.create(business=a, name="ca", source="0")
    cam_b = Camera.objects.create(business=b, name="cb", source="0")
    zona_b = Zone.objects.create(camera=cam_b, name="zb", kind="general",
                                 polygon=[[0, 0], [1, 0], [1, 1]])
    duena_a = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=duena_a, role="owner", business=a)
    return dict(a=a, b=b, cam_a=cam_a, cam_b=cam_b, zona_b=zona_b, duena_a=duena_a)


# --- API DRF: dueña de A apuntando a B ---

@pytest.mark.django_db
@pytest.mark.parametrize("url", ["/api/summary/", "/api/events/"])
def test_api_lectura_de_otro_negocio_es_403(api_client, dos_mundos, url):
    api_client.force_authenticate(dos_mundos["duena_a"])
    r = api_client.get(url, {"business": dos_mundos["b"].pk, "date": "2026-08-12"})
    assert r.status_code == 403


@pytest.mark.django_db
def test_api_listar_camaras_de_otro_negocio_es_403(api_client, dos_mundos):
    api_client.force_authenticate(dos_mundos["duena_a"])
    r = api_client.get("/api/camaras/", {"business": dos_mundos["b"].pk})
    assert r.status_code == 403


@pytest.mark.django_db
def test_api_crear_camara_en_otro_negocio_es_403(api_client, dos_mundos):
    api_client.force_authenticate(dos_mundos["duena_a"])
    r = api_client.post("/api/camaras/",
                        {"business": dos_mundos["b"].pk, "name": "intrusa", "source": "0"})
    assert r.status_code == 403
    assert not Camera.objects.filter(name="intrusa").exists()


@pytest.mark.django_db
@pytest.mark.parametrize("metodo", ["get", "delete"])
def test_api_camara_detalle_de_otro_negocio_no_se_toca(api_client, dos_mundos, metodo):
    api_client.force_authenticate(dos_mundos["duena_a"])
    r = getattr(api_client, metodo)(f"/api/camaras/{dos_mundos['cam_b'].pk}/")
    assert r.status_code in (403, 404)
    assert Camera.objects.filter(pk=dos_mundos["cam_b"].pk).exists()   # no la borró


@pytest.mark.django_db
def test_api_vista_de_camara_ajena_es_403(api_client, dos_mundos):
    api_client.force_authenticate(dos_mundos["duena_a"])
    r = api_client.get(f"/api/camaras/{dos_mundos['cam_b'].pk}/vista/")
    assert r.status_code in (403, 404)


@pytest.mark.django_db
def test_api_zonas_de_camara_ajena_es_403(api_client, dos_mundos):
    api_client.force_authenticate(dos_mundos["duena_a"])
    r = api_client.get(f"/api/camaras/{dos_mundos['cam_b'].pk}/zonas/")
    assert r.status_code in (403, 404)


@pytest.mark.django_db
@pytest.mark.parametrize("metodo", ["put", "delete"])
def test_api_zona_ajena_no_se_modifica(api_client, dos_mundos, metodo):
    api_client.force_authenticate(dos_mundos["duena_a"])
    r = getattr(api_client, metodo)(f"/api/zonas/{dos_mundos['zona_b'].pk}/",
                                    {"name": "hackeada"}, format="json")
    assert r.status_code in (403, 404)
    dos_mundos["zona_b"].refresh_from_db()
    assert dos_mundos["zona_b"].name == "zb"


@pytest.mark.django_db
def test_api_lineas_de_camara_ajena_es_403(api_client, dos_mundos):
    api_client.force_authenticate(dos_mundos["duena_a"])
    r = api_client.get(f"/api/camaras/{dos_mundos['cam_b'].pk}/lineas/")
    assert r.status_code in (403, 404)


@pytest.mark.django_db
@pytest.mark.parametrize("metodo", ["put", "delete"])
def test_api_linea_ajena_no_se_modifica(api_client, dos_mundos, metodo):
    linea = CountingLine.objects.create(camera=dos_mundos["cam_b"], name="lb",
                                        puntos=[[0, 10], [20, 10]])
    api_client.force_authenticate(dos_mundos["duena_a"])
    r = getattr(api_client, metodo)(f"/api/lineas/{linea.pk}/",
                                    {"invertir": True}, format="json")
    assert r.status_code in (403, 404)
    linea.refresh_from_db()
    assert linea.invertir is False


# --- Vistas Django que siguen siendo servidor puro (no el shell de React) ---
# `/` y `/camaras/` son el shell de React: ignoran `?business=` y siempre
# devuelven 200 a quien tenga sesión. El aislamiento por negocio para lo que
# esas pantallas muestran ya está cubierto arriba, contra las mismas APIs
# que el front consume (`/api/summary/`, `/api/camaras/`, etc.).

@pytest.mark.django_db
def test_panel_plataforma_cerrado_a_no_admin(client, dos_mundos):
    client.force_login(dos_mundos["duena_a"])
    assert client.get("/plataforma/").status_code == 403


@pytest.mark.django_db
def test_sistema_cerrado_a_no_admin(client, dos_mundos):
    client.force_login(dos_mundos["duena_a"])
    assert client.get("/sistema/").status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("ruta", ["/reporte/csv/", "/reporte/pdf/"])
def test_reporte_de_otro_negocio_es_403(client, dos_mundos, ruta):
    client.force_login(dos_mundos["duena_a"])
    r = client.get(ruta, {"business": dos_mundos["b"].pk})
    assert r.status_code == 403


# --- Invitaciones: no se cuelan a otro negocio ---

@pytest.mark.django_db
def test_invitar_solo_afecta_al_negocio_propio(client, dos_mundos):
    client.force_login(dos_mundos["duena_a"])
    client.post("/invitar/", {"email": "x@x.com"})
    # la invitación quedó en A, nunca en B
    assert Invitation.objects.filter(business=dos_mundos["a"]).exists()
    assert not Invitation.objects.filter(business=dos_mundos["b"]).exists()


@pytest.mark.django_db
def test_anonimo_no_entra_a_endpoints_de_negocio(client, api_client, dos_mundos):
    assert api_client.get("/api/summary/",
                          {"business": dos_mundos["a"].pk}).status_code in (401, 403)
    r = client.get("/", {"business": dos_mundos["a"].pk})
    assert r.status_code == 302 and "/accounts/login" in r.url
