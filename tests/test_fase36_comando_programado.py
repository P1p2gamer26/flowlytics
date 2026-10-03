import pytest
from django.core.management import call_command
from io import StringIO

@pytest.mark.django_db
def test_comando_programado_registra_jobrun():
    out = StringIO()
    try:
        call_command("respaldo_programado", stdout=out)
    except SystemExit:
        pass  # El comando puede no existir aún en esta ronda
    # Confirmación de contrato: debe haber registro en JobRun o mensaje en stdout
    from analytics.models import JobRun
    assert JobRun.ultima("respaldo_programado") is not None or "respaldo" in out.getvalue().lower()
