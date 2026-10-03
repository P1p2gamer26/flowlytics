"""De dónde sale el umbral de cada aviso: del rubro, salvo que el dueño lo cambie."""
import pytest

from analytics.avisos import reglas_de, umbrales_de
from analytics.models import AlertRule
from tenancy.models import Business


@pytest.fixture
def cafe(db):
    return Business.objects.create(name="Café", kind="cafe")


@pytest.mark.django_db
def test_sin_reglas_propias_manda_el_rubro(cafe):
    assert umbrales_de(cafe)["long_queue"] == 240.0


@pytest.mark.django_db
def test_el_umbral_del_dueño_pisa_el_del_rubro(cafe):
    AlertRule.objects.create(business=cafe, tipo_evento="long_queue",
                             canal="email", destino="d@t.co", umbral=90.0)

    assert umbrales_de(cafe)["long_queue"] == 90.0


@pytest.mark.django_db
def test_una_regla_sin_umbral_no_pisa_nada(cafe):
    # Regla vieja, de antes de esta fase: sigue avisando con el umbral del rubro
    # en vez de dejar al negocio sin detección.
    AlertRule.objects.create(business=cafe, tipo_evento="long_queue",
                             canal="webhook", destino="https://x/y")

    assert umbrales_de(cafe)["long_queue"] == 240.0


@pytest.mark.django_db
def test_desactivar_una_regla_calla_el_aviso_pero_no_apaga_la_medición(cafe):
    # `activa` es cosa de `notificar_evento`. Si apagara la detección, el dueño
    # que dice "no me avises del aforo" perdería el historial de aforo.
    AlertRule.objects.create(business=cafe, tipo_evento="overcrowding",
                             canal="email", destino="d@t.co", umbral=12.0,
                             activa=False)

    assert umbrales_de(cafe)["overcrowding"] == 12.0


@pytest.mark.django_db
def test_las_reglas_de_otro_negocio_no_se_cuelan(cafe):
    otro = Business.objects.create(name="Otro", kind="cafe")
    AlertRule.objects.create(business=otro, tipo_evento="long_queue",
                             canal="email", destino="d@t.co", umbral=5.0)

    assert umbrales_de(cafe)["long_queue"] == 240.0


@pytest.mark.django_db
def test_reglas_de_devuelve_lo_que_el_pipeline_espera(cafe):
    reglas = reglas_de(cafe)

    porumbral = {r.kind: r.threshold for r in reglas}
    assert porumbral["long_queue"] == 240.0
    assert porumbral["crowded_queue"] == 4.0
    # Y son EventRule de verdad, no dicts: `detect_events` lee atributos.
    assert all(hasattr(r, "zone_kind") and hasattr(r, "field") for r in reglas)


@pytest.mark.django_db
def test_un_aula_no_recibe_reglas_de_fila(db):
    aula = Business.objects.create(name="Aula", kind="classroom")

    assert {r.kind for r in reglas_de(aula)} == {"overcrowding"}
