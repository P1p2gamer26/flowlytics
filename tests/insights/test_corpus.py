import pytest

from insights.corpus import MIN_COHORTE, hash_negocio
from insights.models import CorpusEntry
from tenancy.models import Business


@pytest.mark.django_db
def test_hash_es_estable_para_el_mismo_negocio():
    biz = Business.objects.create(name="Cafe Uno", kind="cafe")

    assert hash_negocio(biz) == hash_negocio(biz)


@pytest.mark.django_db
def test_hash_difiere_entre_negocios():
    a = Business.objects.create(name="Cafe Uno", kind="cafe")
    b = Business.objects.create(name="Cafe Dos", kind="cafe")

    assert hash_negocio(a) != hash_negocio(b)


@pytest.mark.django_db
def test_hash_no_contiene_el_nombre_ni_el_id():
    biz = Business.objects.create(name="Cafe Uno", kind="cafe")

    h = hash_negocio(biz)

    assert "Cafe" not in h
    assert str(biz.pk) != h
    assert len(h) == 16


@pytest.mark.django_db
def test_corpus_entry_no_tiene_campo_hacia_business():
    """Si alguien agrega un FK a Business, el corpus deja de ser anónimo."""
    campos = {f.name for f in CorpusEntry._meta.get_fields()}

    assert "business" not in campos
    assert "business_id" not in campos


@pytest.mark.django_db
def test_negocio_comparte_corpus_por_defecto():
    biz = Business.objects.create(name="Cafe Uno", kind="cafe")

    assert biz.comparte_corpus is True


def test_min_cohorte_es_cinco():
    assert MIN_COHORTE == 5


from datetime import date, datetime, timezone as dt_tz

from analytics.models import MetricWindow
from cameras.models import Camera
from insights.corpus import extraer_entrada


@pytest.fixture
def negocio_con_datos(db):
    biz = Business.objects.create(name="Cafe Uno", kind="cafe")
    cam = Camera.objects.create(business=biz, name="c", source="0")
    MetricWindow.objects.create(
        camera=cam, zone_name="fila", zone_kind="queue",
        started_at=datetime(2026, 8, 12, 13, 0, tzinfo=dt_tz.utc),
        ended_at=datetime(2026, 8, 12, 13, 1, tzinfo=dt_tz.utc),
        occupancy_avg=4.0, occupancy_max=9, dwell_seconds=210.0, unique_visitors=30)
    return biz


@pytest.mark.django_db
def test_extrae_metricas_del_dia(negocio_con_datos):
    entrada = extraer_entrada(negocio_con_datos, date(2026, 8, 12))

    assert entrada is not None
    assert entrada.cohorte == "cafe"
    assert entrada.visitantes == 30
    assert entrada.aforo_pico == 9
    assert entrada.espera_fila_seg == 210.0


@pytest.mark.django_db
def test_no_extrae_si_el_negocio_opto_por_no_compartir(negocio_con_datos):
    negocio_con_datos.comparte_corpus = False
    negocio_con_datos.save()

    assert extraer_entrada(negocio_con_datos, date(2026, 8, 12)) is None
    assert CorpusEntry.objects.count() == 0


@pytest.mark.django_db
def test_no_extrae_si_no_hubo_datos_ese_dia(negocio_con_datos):
    assert extraer_entrada(negocio_con_datos, date(2026, 8, 11)) is None


@pytest.mark.django_db
def test_reejecutar_actualiza_en_vez_de_duplicar(negocio_con_datos):
    extraer_entrada(negocio_con_datos, date(2026, 8, 12))
    extraer_entrada(negocio_con_datos, date(2026, 8, 12))

    assert CorpusEntry.objects.count() == 1


@pytest.mark.django_db
def test_la_entrada_no_permite_identificar_al_negocio(negocio_con_datos):
    entrada = extraer_entrada(negocio_con_datos, date(2026, 8, 12))

    serializado = str(entrada.__dict__)
    assert "Cafe Uno" not in serializado
    assert f"'{negocio_con_datos.pk}'" not in serializado
