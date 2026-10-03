import pytest
from analytics.models import JobRun

@pytest.mark.django_db
def test_jobrun_registra_respaldo_automatico():
    JobRun.marcar("respaldo_automatico", ok=True, detalle="respaldo_2026-09-25.tar.gz")
    ultimo = JobRun.ultima("respaldo_automatico")
    assert ultimo is not None
    assert ultimo.ok is True
    assert "respaldo" in ultimo.detalle

@pytest.mark.django_db
def test_jobrun_registra_fallo_tambien():
    JobRun.marcar("respaldo_automatico", ok=False, detalle="archivo_no_creado")
    ultimo = JobRun.ultima("respaldo_automatico")
    assert ultimo.ok is False
    assert "archivo" in ultimo.detalle
