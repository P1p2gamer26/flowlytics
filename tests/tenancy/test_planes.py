import pytest

from cameras.models import Camera
from tenancy.models import Business, Plan, PLAN_POR_DEFECTO


@pytest.mark.django_db
def test_negocio_sin_plan_usa_los_limites_por_defecto():
    biz = Business.objects.create(name="Sin plan", kind="cafe")
    assert biz.plan is None
    assert biz.max_camaras == PLAN_POR_DEFECTO["max_camaras"]
    assert biz.retencion_dias == PLAN_POR_DEFECTO["retencion_dias"]


@pytest.mark.django_db
def test_negocio_con_plan_usa_los_limites_del_plan():
    plan = Plan.objects.create(nombre="Pro", max_camaras=5, retencion_dias=365)
    biz = Business.objects.create(name="Con plan", kind="retail", plan=plan)
    assert biz.max_camaras == 5
    assert biz.retencion_dias == 365


@pytest.mark.django_db
def test_puede_agregar_camara_respeta_el_limite():
    plan = Plan.objects.create(nombre="Chico", max_camaras=1)
    biz = Business.objects.create(name="Tope", kind="cafe", plan=plan)
    assert biz.puede_agregar_camara() is True
    Camera.objects.create(business=biz, name="c1", source="0")
    assert biz.puede_agregar_camara() is False
