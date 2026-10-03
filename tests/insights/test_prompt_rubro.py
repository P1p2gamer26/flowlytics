"""El prompt le dice al modelo qué le importa a este rubro.

Sin esto, el LLM recomienda lo mismo para un aula que para un supermercado.
"""
import pytest

from insights.prompt import build_prompt
from tenancy.models import Business

SUMMARY = {"date": "2026-09-01", "total_visitors": 340, "peak_occupancy": 13,
           "peak_hour": 18, "avg_queue_seconds": 210.5, "avg_dwell_seconds": 900.0,
           "staff_coverage_pct": 88.0, "hourly": [], "zones": []}


@pytest.mark.django_db
def test_el_prompt_de_un_cafe_habla_de_la_mesa():
    prompt = build_prompt(SUMMARY, Business.objects.create(name="Cafe", kind="cafe"))

    assert "mesa" in prompt.lower()


@pytest.mark.django_db
def test_el_prompt_de_una_tienda_habla_de_la_caja():
    prompt = build_prompt(SUMMARY, Business.objects.create(name="Tienda", kind="retail"))

    assert "caja" in prompt.lower()
    assert "mesa" not in prompt.lower().split("guía de interpretación")[0]


@pytest.mark.django_db
def test_un_kind_desconocido_no_rompe_el_prompt():
    biz = Business.objects.create(name="Raro", kind="marciano")

    prompt = build_prompt(SUMMARY, biz)

    assert "Raro" in prompt
    assert "{foco}" not in prompt


@pytest.mark.django_db
def test_el_prompt_explica_la_permanencia_nueva():
    prompt = build_prompt(SUMMARY, Business.objects.create(name="Cafe", kind="cafe"))

    assert "avg_dwell_seconds" in prompt
