import pytest
from insights.models import CorpusEntry

@pytest.mark.django_db
def test_corpus_entry_no_tiene_campos_sensibles():
    campos = {f.name for f in CorpusEntry._meta.get_fields()}
    sensibles = {"business", "business_id", "track_id", "pistas", "nombre"}
    encontrados = sensibles & campos
    assert len(encontrados) == 0, f"Campos sensibles encontrados: {encontrados}"
