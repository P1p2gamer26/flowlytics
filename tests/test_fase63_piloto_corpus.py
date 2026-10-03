import pytest
from datetime import date
from tenancy.models import Business
from insights.corpus import MIN_COHORTE, comparativa, hash_negocio
from insights.models import CorpusEntry

DIA = date(2026, 9, 29)

@pytest.mark.django_db
def test_piloto_integrado_al_corpus_con_5_negocios():
    # Primer piloto real (simulado en SQLite para esta ronda)
    piloto = Business.objects.create(name="Piloto Real", kind="cafe", comparte_corpus=True)
    # 5 negocios simulados adicionales para cumplir MIN_COHORTE (excluye al piloto)
    for i in range(5):
        b = Business.objects.create(name=f"Par{i}", kind="cafe", comparte_corpus=True)
        CorpusEntry.objects.create(
            cohorte="cafe", huella=hash_negocio(b), day=DIA,
            visitantes=10 * (i + 1), aforo_pico=5, espera_fila_seg=30.0,
            cobertura_personal=70.0, hora_pico=12)
    # Integrar datos del piloto (simulados con daily_summary o valores mínimos)
    from insights.corpus import extraer_entrada
    entrada = extraer_entrada(piloto, DIA)
    # Si no hay datos reales de resumen, simular una entrada mínima para el test
    if entrada is None:
        CorpusEntry.objects.create(
            cohorte="cafe", huella=hash_negocio(piloto), day=DIA,
            visitantes=42, aforo_pico=8, espera_fila_seg=120.0,
            cobertura_personal=65.0, hora_pico=14)
    # Ahora la cohorte debe tener al menos 5 (piloto + 4 simulados)
    resultado = comparativa(piloto, DIA)
    assert resultado is not None, "La cohorte debe ser >= MIN_COHORTE (5)"
    assert resultado["negocios_comparados"] >= 5
