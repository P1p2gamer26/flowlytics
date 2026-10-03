import pytest

from vision.humo import comparar_muestreos


@pytest.mark.django_db
def test_dice_si_el_conteo_es_estable():
    medidas = {2: 40, 6: 44}
    r = comparar_muestreos(medidas)
    assert r["estable"] is True
    assert r["desvio_pct"] == pytest.approx(10.0, abs=0.1)


@pytest.mark.django_db
def test_dice_que_no_lo_es_y_no_lo_disimula():
    r = comparar_muestreos({2: 42, 6: 120})
    assert r["estable"] is False
    assert r["desvio_pct"] > 100
