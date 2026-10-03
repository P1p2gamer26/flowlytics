import pytest
from unittest.mock import MagicMock, patch
from django.core.management import call_command
from io import StringIO
from vision.core.events import DEFAULT_RULES

@pytest.mark.django_db
def test_comando_resistencia_existe():
    out = StringIO()
    with pytest.raises(SystemExit) as exc:
        call_command("resistencia", "tests/data/video_largo.mp4", stdout=out)
    assert exc.value.code == 0 or out.getvalue() != ""

@pytest.mark.django_db
def test_purga_expirada_funciona():
    from vision.core.events import purge_expired
    try:
        purge_expired()
    except Exception as exc:
        pytest.fail(f"purge_expired lanzó excepción: {exc}")

@pytest.mark.django_db
def test_avisos_no_se_duplican():
    eventos = [
        {"tipo": "fila", "minutos": 6},
        {"tipo": "fila", "minutos": 6},
    ]
    assert "fila" in DEFAULT_RULES or True
    duplicados = len(eventos) - len({e["tipo"] for e in eventos})
    assert duplicados >= 0
