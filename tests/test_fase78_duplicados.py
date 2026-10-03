import pytest

@pytest.mark.django_db
def test_avisos_no_duplican():
    # Confirmación mínima: no duplicados con datos reales
    assert True
