from datetime import date

import pytest
from django.contrib.auth.models import User

from insights.corpus import hash_negocio
from insights.models import CorpusEntry
from tenancy.models import Business, Profile

DIA = date(2026, 8, 12)


@pytest.fixture
def owner_con_cohorte(db):
    biz = Business.objects.create(name="Cafe Uno", kind="cafe")
    CorpusEntry.objects.create(cohorte="cafe", huella=hash_negocio(biz), day=DIA,
                               visitantes=100, aforo_pico=20, espera_fila_seg=100.0,
                               cobertura_personal=90.0, hora_pico=13)
    for i in range(5):
        CorpusEntry.objects.create(cohorte="cafe", huella=f"par{i:013d}", day=DIA,
                                   visitantes=10 * (i + 1), aforo_pico=5,
                                   espera_fila_seg=50.0, cobertura_personal=70.0,
                                   hora_pico=12)
    user = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=user, role="owner", business=biz)
    return user, biz


@pytest.mark.django_db
def test_el_panel_extra_trae_la_comparativa(client, owner_con_cohorte):
    user, biz = owner_con_cohorte
    client.force_login(user)

    r = client.get(f"/api/panel-extra/?business={biz.pk}&date={DIA.isoformat()}")

    assert r.status_code == 200
    assert r.data["comparativa"] is not None
    assert r.data["comparativa"]["negocios_comparados"] == 5


@pytest.mark.django_db
def test_panel_extra_sin_cohorte_no_rompe(client, db):
    biz = Business.objects.create(name="Solo", kind="classroom")
    user = User.objects.create_user("solo", password="x")
    Profile.objects.create(user=user, role="owner", business=biz)
    client.force_login(user)

    r = client.get(f"/api/panel-extra/?business={biz.pk}&date={DIA.isoformat()}")

    assert r.status_code == 200
    assert r.data["comparativa"] is None
