from datetime import datetime, timedelta, timezone as dt_timezone
from types import SimpleNamespace

from vision.management.commands.watchdog import revisar

T0 = datetime(2026, 8, 14, 12, 0, tzinfo=dt_timezone.utc)


def _cam_caida(nombre, business_id):
    return SimpleNamespace(camera=SimpleNamespace(name=nombre, business_id=business_id))


def _sin_hallazgos(**over):
    base = dict(ahora=T0, camaras_caidas=[],
                jobs_ultima={"corpus": T0, "insights": T0, "backup": T0},
                uso_disco=0.5, clips_vencidos_en_disco=0,
                restore_check_dias=1)
    base.update(over)
    return base


def _tipos(hallazgos):
    return {h["tipo"] for h in hallazgos}


def test_todo_sano_no_reporta_nada():
    assert revisar(**_sin_hallazgos()) == []


def test_camara_sin_senal_se_reporta():
    h = revisar(**_sin_hallazgos(camaras_caidas=[_cam_caida("Barra", 7)]))
    assert _tipos(h) == {"camara_caida"}
    assert h[0]["business_id"] == 7


def test_job_que_no_corrio_se_reporta():
    viejo = {"corpus": T0 - timedelta(hours=30), "insights": T0, "backup": T0}
    h = revisar(**_sin_hallazgos(jobs_ultima=viejo))
    assert "job" in _tipos(h)


def test_job_que_nunca_corrio_se_reporta():
    h = revisar(**_sin_hallazgos(jobs_ultima={"insights": T0, "backup": T0}))
    assert "job" in _tipos(h)


def test_disco_lleno_se_reporta():
    assert "disco" in _tipos(revisar(**_sin_hallazgos(uso_disco=0.95)))


def test_clips_vencidos_en_disco_se_reportan():
    assert "clips" in _tipos(revisar(**_sin_hallazgos(clips_vencidos_en_disco=4)))


def test_restore_check_viejo_se_reporta():
    assert "backup" in _tipos(revisar(**_sin_hallazgos(restore_check_dias=5)))
    assert "backup" in _tipos(revisar(**_sin_hallazgos(restore_check_dias=None)))
