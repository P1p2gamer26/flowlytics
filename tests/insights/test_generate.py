from datetime import date, datetime, timezone as dt_tz

import pytest

from analytics.models import MetricWindow
from cameras.models import Camera
from insights.client import FakeLlmClient
from insights.models import Insight
from insights.services import generate_for_business
from tenancy.models import Business


@pytest.fixture
def business_with_data(db):
    biz = Business.objects.create(name="Cafe Uno", kind="cafe")
    cam = Camera.objects.create(business=biz, name="c", source="0")
    MetricWindow.objects.create(
        camera=cam, zone_name="fila", zone_kind="queue",
        started_at=datetime(2026, 8, 12, 13, 0, tzinfo=dt_tz.utc),
        ended_at=datetime(2026, 8, 12, 13, 1, tzinfo=dt_tz.utc),
        occupancy_avg=4.0, occupancy_max=9, dwell_seconds=210.0, unique_visitors=30)
    return biz


@pytest.mark.django_db
def test_creates_insight_from_llm_response(business_with_data):
    llm = FakeLlmClient(canned="## Qué corregir\n- la fila tarda 210s")

    insight = generate_for_business(business_with_data, date(2026, 8, 12), llm)

    assert insight.body == "## Qué corregir\n- la fila tarda 210s"
    assert insight.model == "fake-model"
    assert Insight.objects.count() == 1


@pytest.mark.django_db
def test_rerunning_updates_instead_of_duplicating(business_with_data):
    generate_for_business(business_with_data, date(2026, 8, 12), FakeLlmClient("v1"))
    generate_for_business(business_with_data, date(2026, 8, 12), FakeLlmClient("v2"))

    assert Insight.objects.count() == 1
    assert Insight.objects.first().body == "v2"


@pytest.mark.django_db
def test_skips_business_with_no_data_for_that_day(business_with_data):
    llm = FakeLlmClient()

    result = generate_for_business(business_with_data, date(2026, 8, 11), llm)

    assert result is None
    assert Insight.objects.count() == 0
    assert llm.prompts == []   # no se gastó una llamada al LLM
