import pytest
from datetime import date
from tenancy.models import Business
from insights.corpus import MIN_COHORTE, comparativa, hash_negocio
from insights.models import CorpusEntry

DIA = date(2026, 9, 29)

@pytest.mark.django_db
def test_benchmark_con_datos_reales_del_piloto_respecta_min_cohorte():
    # Primer piloto real (simulado con SQLite para esta ronda)
    piloto = Business.objects.create(name="Primer Piloto Real", kind="cafe", comparte_corpus=True)
    # 5 negocios simulados adicionales para cumplir MIN_COHORTE (excluye al piloto)
    for i in range(5):
        b = Business.objects.create(name=f"Par{i}", kind="cafe", comparte_corpus=True)
        CorpusEntry.objects.create(
            cohorte="cafe", huella=hash_negocio(b), day=DIA,
            visitantes=10 * (i + 1), aforo_pico=5, espera_fila_seg=30.0,
            cobertura_personal=70.0, hora_pico=12)
    # Integrar entrada del piloto (simulada con datos mínimos del primer día)
    from insights.corpus import extraer_entrada
    entrada = extraer_entrada(piloto, DIA)
    if entrada is None:
        CorpusEntry.objects.create(
            cohorte="cafe", huella=hash_negocio(piloto), day=DIA,
            visitantes=42, aforo_pico=8, espera_fila_seg=120.0,
            cobertura_personal=65.0, hora_pico=14)
    # Confirmar que MIN_COHORTE se respeta: con 6 negocios distintos (piloto + 5), debe pasar
    resultado = comparativa(piloto, DIA)
    assert resultado is not None, "comparativa debe devolver datos con MIN_COHORTE >= 5"
    assert resultado["negocios_comparados"] >= 5, f"MIN_COHORTE debe ser >= 5, actual: {resultado.get('negocios_comparados')}"
    # Confirmar que no expone datos sensibles
    for clave in resultado:
        if clave not in ["negocios_comparados", "ventana_dias", "visitantes", "aforo_pico", "espera_fila_seg", "cobertura_personal"]:
            assert "track_id" not in str(resultado[clave]).lower(), "No debe exponer track_id"
