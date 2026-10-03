"""Invariantes de privacidad del corpus. Si alguno falla, hay una fuga de datos."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_corpus_entry_no_declara_foreign_keys():
    fuente = (ROOT / "insights" / "models.py").read_text(encoding="utf-8")
    clase = fuente.split("class CorpusEntry")[1]
    assert "ForeignKey" not in clase
    assert "OneToOne" not in clase


def test_min_cohorte_se_usa_y_no_esta_hardcodeado():
    fuente = (ROOT / "insights" / "corpus.py").read_text(encoding="utf-8")
    assert "MIN_COHORTE" in fuente
    # el número suelto solo puede aparecer en la definición de la constante
    assert fuente.count("< 5") == 0


@pytest.mark.django_db
def test_la_comparativa_nunca_devuelve_huellas():
    from datetime import date

    from insights.corpus import comparativa, hash_negocio
    from insights.models import CorpusEntry
    from tenancy.models import Business

    biz = Business.objects.create(name="X", kind="cafe")
    CorpusEntry.objects.create(cohorte="cafe", huella=hash_negocio(biz),
                               day=date(2026, 8, 12), visitantes=100, aforo_pico=10)
    for i in range(5):
        CorpusEntry.objects.create(cohorte="cafe", huella=f"p{i:015d}",
                                   day=date(2026, 8, 12), visitantes=10, aforo_pico=2)

    resultado = comparativa(biz, date(2026, 8, 12))

    assert "huella" not in str(resultado)
    assert "p000" not in str(resultado)
