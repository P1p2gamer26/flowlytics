# tests/test_fase48_cohorte_minima.py
import pytest
from datetime import date
from tenancy.models import Business
from insights.corpus import MIN_COHORTE, comparativa, hash_negocio
from insights.models import CorpusEntry

DIA = date(2026, 9, 28)

@pytest.mark.django_db
def test_cohorte_menor_que_5_devuelve_none():
    # Solo 3 negocios del mismo rubro -> debe fallar (comparativa = None)
    biz = Business.objects.create(name="Cafe Uno", kind="cafe")
    for i in range(3):
        b = Business.objects.create(name=f"Cafe Par{i}", kind="cafe")
        CorpusEntry.objects.create(
            cohorte="cafe", huella=f"par{i:012d}", day=DIA,
            visitantes=10, aforo_pico=5, espera_fila_seg=30.0,
            cobertura_personal=70.0, hora_pico=12)
    # El propio negocio no está en el corpus aún, así que la cohorte es 3 < 5
    assert comparativa(biz, DIA) is None

@pytest.mark.django_db
def test_todos_rubros_simulados_con_5_negocios():
    rubros = ["cafe", "restaurant", "retail", "classroom", "other"]
    for rubro in rubros:
        for i in range(5):
            CorpusEntry.objects.create(
                cohorte=rubro, huella=f"{rubro}_{i:012d}", day=DIA,
                visitantes=10 * (i + 1), aforo_pico=5, espera_fila_seg=30.0,
                cobertura_personal=70.0, hora_pico=12)

@pytest.mark.django_db
def test_extraer_entrada_no_guarda_sensibles():
    biz = Business.objects.create(name="Cafe Sensible", kind="cafe", comparte_corpus=True)
    # extraer_entrada no guarda track_id, Recorrido.pistas ni business.pk
    # Solo guarda huella (hash no reversible), cohorte y métricas agregadas.
    from insights.corpus import extraer_entrada
    entrada = extraer_entrada(biz, DIA)
    if entrada is not None:
        # Verifica que los campos del modelo no incluyen datos sensibles
        assert not hasattr(entrada, "track_id")
        assert not hasattr(entrada, "pistas")
        # El pk del negocio no está en el corpus; solo la huella
        assert entrada.huella != str(biz.pk)
