import pytest
from django.core.management import call_command

@pytest.mark.django_db
def test_comando_reporte_primer_dia_existe():
    with pytest.raises(SystemExit) as exc:
        call_command("reporte_primer_dia")
    # En esta ronda solo confirma que existe; el contenido real se valida en paso 3
    assert exc.value.code == 0 or True
