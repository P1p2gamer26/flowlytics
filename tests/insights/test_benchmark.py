from datetime import date, timedelta

import pytest

from insights.corpus import MIN_COHORTE, comparativa, hash_negocio
from insights.models import CorpusEntry
from tenancy.models import Business

DIA = date(2026, 8, 12)


def sembrar_cohorte(cohorte, valores, day=DIA):
    """Crea una entrada por cada valor de visitantes, con huellas distintas."""
    for i, visitantes in enumerate(valores):
        CorpusEntry.objects.create(
            cohorte=cohorte, huella=f"pares{i:012d}", day=day,
            visitantes=visitantes, aforo_pico=visitantes // 3,
            espera_fila_seg=float(visitantes), cobertura_personal=80.0,
            hora_pico=13)


@pytest.fixture
def mi_negocio(db):
    biz = Business.objects.create(name="Cafe Uno", kind="cafe")
    CorpusEntry.objects.create(
        cohorte="cafe", huella=hash_negocio(biz), day=DIA,
        visitantes=100, aforo_pico=20, espera_fila_seg=100.0,
        cobertura_personal=90.0, hora_pico=13)
    return biz


@pytest.mark.django_db
def test_devuelve_none_si_la_cohorte_es_muy_pequena(mi_negocio):
    sembrar_cohorte("cafe", [50, 60, 70])   # 3 pares + yo = 4 < MIN_COHORTE

    assert comparativa(mi_negocio, DIA) is None


@pytest.mark.django_db
def test_devuelve_datos_al_alcanzar_la_cohorte_minima(mi_negocio):
    sembrar_cohorte("cafe", [10, 20, 30, 40, 50])

    resultado = comparativa(mi_negocio, DIA)

    assert resultado is not None
    assert resultado["negocios_comparados"] == 5
    assert resultado["visitantes"]["propio"] == 100
    assert resultado["visitantes"]["mediana_pares"] == 30


@pytest.mark.django_db
def test_excluye_al_propio_negocio_de_la_mediana(mi_negocio):
    # Si se incluyera a sí mismo (100), la mediana de [10,20,30,40,50,100] seria 35
    sembrar_cohorte("cafe", [10, 20, 30, 40, 50])

    resultado = comparativa(mi_negocio, DIA)

    assert resultado["visitantes"]["mediana_pares"] == 30


@pytest.mark.django_db
def test_no_mezcla_cohortes_distintas(mi_negocio):
    sembrar_cohorte("restaurant", [1, 2, 3, 4, 5, 6, 7])

    assert comparativa(mi_negocio, DIA) is None


@pytest.mark.django_db
def test_percentil_ubica_al_negocio_en_su_cohorte(mi_negocio):
    sembrar_cohorte("cafe", [10, 20, 30, 40, 50])

    resultado = comparativa(mi_negocio, DIA)

    # 100 supera a los 5 pares -> percentil 100
    assert resultado["visitantes"]["percentil"] == 100


@pytest.mark.django_db
def test_ignora_dias_fuera_de_la_ventana(mi_negocio):
    sembrar_cohorte("cafe", [10, 20, 30, 40, 50], day=DIA - timedelta(days=60))

    assert comparativa(mi_negocio, DIA, ventana_dias=30) is None
