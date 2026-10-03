"""`/api/summary/` trae, además de los números, qué hacer con ellos.

Va en el mismo endpoint porque el panel los pinta juntos y el rubro no cambia
entre peticiones: pedirlo aparte sería una ronda de red por una constante.
"""
import pytest


@pytest.mark.django_db
def test_el_resumen_trae_el_perfil_del_rubro(client_demo, camara_demo):
    # camara_demo pertenece a un negocio de kind="cafe".
    r = client_demo.get(f"/api/summary/?business={camara_demo.business.pk}")

    assert r.status_code == 200
    rubro = r.data["rubro"]
    assert rubro["principal"] == "avg_dwell_seconds"
    assert rubro["metricas"][0] == "avg_dwell_seconds"
    assert rubro["etiquetas"]["avg_dwell_seconds"] == "Permanencia en mesa"
    assert {"name": "Mesas", "kind": "general"} in rubro["zonas"]
    assert "mesa" in rubro["foco"].lower()


@pytest.mark.django_db
def test_dos_rubros_distintos_piden_cifras_distintas(client_demo, camara_demo):
    negocio = camara_demo.business
    cafe = client_demo.get(f"/api/summary/?business={negocio.pk}").data["rubro"]

    negocio.kind = "retail"
    negocio.save(update_fields=["kind"])
    tienda = client_demo.get(f"/api/summary/?business={negocio.pk}").data["rubro"]

    assert cafe["principal"] != tienda["principal"]
    assert tienda["etiquetas"]["avg_queue_seconds"] == "Cola en caja"


@pytest.mark.django_db
def test_un_kind_desconocido_no_deja_el_panel_sin_cifras(client_demo, camara_demo):
    # `save()` no valida choices: un dato viejo o importado puede traer cualquier cosa.
    negocio = camara_demo.business
    negocio.kind = "lo-que-sea"
    negocio.save(update_fields=["kind"])

    r = client_demo.get(f"/api/summary/?business={negocio.pk}")

    assert r.status_code == 200
    assert r.data["rubro"]["metricas"]


@pytest.mark.django_db
def test_las_metricas_del_rubro_existen_en_el_resumen_servido(client_demo, camara_demo):
    # El contrato que de verdad importa: lo que el rubro manda pintar, el resumen
    # lo trae. Si no, el panel muestra guiones para siempre.
    r = client_demo.get(f"/api/summary/?business={camara_demo.business.pk}")

    for clave in r.data["rubro"]["metricas"]:
        assert clave in r.data, f"el rubro pide {clave} y el resumen no lo trae"


@pytest.mark.django_db
def test_el_resumen_de_otro_negocio_sigue_prohibido(client_demo, camara_demo, db):
    from tenancy.models import Business

    ajeno = Business.objects.create(name="Ajeno", kind="retail")

    r = client_demo.get(f"/api/summary/?business={ajeno.pk}")

    assert r.status_code in (403, 404)
