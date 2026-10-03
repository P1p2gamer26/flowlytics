import pytest
from datetime import date
from django.contrib.auth.models import User
from tenancy.models import Business, Profile
from insights.corpus import MIN_COHORTE, hash_negocio, comparativa
from insights.models import CorpusEntry

DIA = date(2026, 9, 28)

@pytest.fixture
def dueño_con_cohorte(db):
    biz = Business.objects.create(name="Cafe Prueba", kind="cafe")
    # 5 negocios de la misma cohorte en el corpus
    for i in range(5):
        CorpusEntry.objects.create(
            cohorte="cafe", huella=f"par{i:012d}", day=DIA,
            visitantes=10 * (i + 1), aforo_pico=5,
            espera_fila_seg=30.0, cobertura_personal=70.0, hora_pico=12)
    # El propio negocio también debe estar en el corpus
    CorpusEntry.objects.create(
        cohorte="cafe", huella=hash_negocio(biz), day=DIA,
        visitantes=80, aforo_pico=15, espera_fila_seg=45.0,
        cobertura_personal=85.0, hora_pico=13)
    # Simular 5 negocios por rubro
    rubros = ["cafe", "restaurant", "retail", "classroom", "other"]
    for rubro in rubros:
        cohorte = rubro if rubro in ["cafe", "restaurant", "retail"] else "other"
        for i in range(5):
            CorpusEntry.objects.create(
                cohorte=cohorte, huella=f"sim{rubro}{i:012d}", day=DIA,
                visitantes=10 * (i + 1), aforo_pico=5,
                espera_fila_seg=30.0, cobertura_personal=70.0, hora_pico=12)

    user = User.objects.create_user("dueno", password="x")
    Profile.objects.create(user=user, role="owner", business=biz)
    return user, biz

@pytest.mark.django_db
def test_panel_extra_trae_percentil_y_mediana(client, dueño_con_cohorte):
    user, biz = dueño_con_cohorte
    client.force_login(user)
    r = client.get(f"/api/panel-extra/?business={biz.pk}&date={DIA.isoformat()}")
    assert r.status_code == 200
    comp = r.data["comparativa"]
    assert comp is not None
    assert "visitantes" in comp
    assert "percentil" in comp["visitantes"]
    assert "mediana_pares" in comp["visitantes"]
    # No debe exponer datos sensibles
    assert "huella" not in r.content.decode()
    assert "track_id" not in r.content.decode()
    assert "pistas" not in r.content.decode()
