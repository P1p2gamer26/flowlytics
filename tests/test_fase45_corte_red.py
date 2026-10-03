import pytest

@pytest.mark.django_db
def test_doble_red_simula_corte():
    from tests.double_red import DobleRed
    red = DobleRed()
    red.cortar()
    assert red.tiempo_corte() > 0, "El doble debe simular un corte de red"
    red.restablecer()
    assert not red.cortada(), "Al restablecer, la red debe estar activa"
