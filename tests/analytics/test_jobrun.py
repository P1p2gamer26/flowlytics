import pytest

from analytics.models import JobRun


@pytest.mark.django_db
def test_marcar_crea_una_fila():
    JobRun.marcar("corpus")
    assert JobRun.ultima("corpus").ok is True


@pytest.mark.django_db
def test_marcar_actualiza_en_vez_de_duplicar():
    JobRun.marcar("corpus", ok=True)
    JobRun.marcar("corpus", ok=False, detalle="sin datos")

    assert JobRun.objects.filter(nombre="corpus").count() == 1
    ultima = JobRun.ultima("corpus")
    assert ultima.ok is False
    assert ultima.detalle == "sin datos"


@pytest.mark.django_db
def test_ultima_de_un_job_desconocido_es_none():
    assert JobRun.ultima("no-existe") is None
