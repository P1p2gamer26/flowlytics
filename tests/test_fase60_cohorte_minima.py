import pytest
from datetime import date
from tenancy.models import Business
from insights.corpus import MIN_COHORTE, comparativa, hash_negocio
from insights.models import CorpusEntry

DIA = date(2026, 9, 29)

@pytest.mark.django_db
def test_cohorte_menor_que_5_devuelve_none():
    # Solo 3 negocios del mismo rubro -> debe fallar (comparativa = None)
    biz = Business.objects.create(name="Supermercado Uno", kind="supermercado")
    for i in range(3):
        b = Business.objects.create(name=f"Supermercado Par{i}", kind="supermercado")
        CorpusEntry.objects.create(
            cohorte="supermercado", huella=f"par{i:012d}", day=DIA,
            visitantes=10, aforo_pico=5, espera_fila_seg=30.0,
            cobertura_personal=70.0, hora_pico=12)
    # El propio negocio no está en el corpus aún, así que la cohorte es 3 < 5
    assert comparativa(biz, DIA) is None

    # Añadir al test: simular 5 negocios por cada rubro definido
    rubros = ["supermercado", "cafe", "drogueria", "tienda_barrio"]
    for rubro in rubros:
        for i in range(5):
            CorpusEntry.objects.create(
                cohorte=rubro, huella=f"sim{rubro[:4]}{i:012d}", day=DIA,
                visitantes=10 * (i + 1), aforo_pico=5, espera_fila_seg=30.0,
                cobertura_personal=70.0, hora_pico=12)
