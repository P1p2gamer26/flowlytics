import pytest

from insights.prompt import build_prompt
from tenancy.models import Business

SUMMARY = {
    "date": "2026-08-12",
    "business": "Cafe Uno",
    "total_visitors": 340,
    "peak_occupancy": 22,
    "peak_hour": 13,
    "avg_queue_seconds": 210.5,
    "staff_coverage_pct": 78.0,
    "hourly": [{"hour": 9, "occupancy_avg": 3.1, "visitors": 40},
               {"hour": 13, "occupancy_avg": 15.0, "visitors": 150}],
    "zones": [{"zone_name": "fila", "zone_kind": "queue", "occupancy_avg": 4.2,
               "dwell_seconds": 210.5, "visitors": 300}],
}


@pytest.mark.django_db
def test_prompt_includes_the_key_numbers():
    biz = Business.objects.create(name="Cafe Uno", kind="cafe")

    prompt = build_prompt(SUMMARY, biz)

    assert "340" in prompt
    assert "210.5" in prompt or "210" in prompt
    assert "13" in prompt


@pytest.mark.django_db
def test_prompt_mentions_the_business_kind_for_context():
    biz = Business.objects.create(name="Aula 3", kind="classroom")

    prompt = build_prompt(SUMMARY, biz)

    assert "classroom" in prompt.lower() or "aula" in prompt.lower()


@pytest.mark.django_db
def test_prompt_never_contains_tracker_ids_or_image_data():
    biz = Business.objects.create(name="Cafe Uno", kind="cafe")

    prompt = build_prompt(SUMMARY, biz)

    assert "tracker_id" not in prompt
    assert "base64" not in prompt
    assert "data:image" not in prompt


COMPARATIVA = {
    "negocios_comparados": 8,
    "ventana_dias": 30,
    "visitantes": {"propio": 340, "mediana_pares": 210, "percentil": 88},
    "espera_fila_seg": {"propio": 210.5, "mediana_pares": 95.0, "percentil": 95},
}


@pytest.mark.django_db
def test_prompt_incluye_la_comparativa_cuando_existe():
    biz = Business.objects.create(name="Cafe Uno", kind="cafe")

    prompt = build_prompt(SUMMARY, biz, comparativa=COMPARATIVA)

    assert "8" in prompt
    assert "210" in prompt
    assert "percentil" in prompt.lower()


@pytest.mark.django_db
def test_prompt_sin_comparativa_no_inventa_la_seccion():
    biz = Business.objects.create(name="Cafe Uno", kind="cafe")

    prompt = build_prompt(SUMMARY, biz, comparativa=None)

    assert "percentil" not in prompt.lower()
    assert "cohorte" not in prompt.lower()


@pytest.mark.django_db
def test_la_comparativa_no_expone_negocios_concretos():
    biz = Business.objects.create(name="Cafe Uno", kind="cafe")

    prompt = build_prompt(SUMMARY, biz, comparativa=COMPARATIVA)

    assert "huella" not in prompt
    assert "business_id" not in prompt
