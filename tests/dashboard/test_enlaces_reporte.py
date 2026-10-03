import pytest
from django.contrib.auth.models import User

from tenancy.models import Business, Profile


@pytest.fixture
def duena(db):
    biz = Business.objects.create(name="Neg", kind="cafe")
    user = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=user, role="owner", business=biz)
    return user, biz


@pytest.mark.django_db
def test_las_rutas_de_descarga_que_arma_el_panel_funcionan(client, duena):
    """El panel de React arma los enlaces de descarga como `<a href>` directos
    (no salen de una API): lo que hay que probar es que esas rutas, con el
    business que el panel conoce, responden."""
    user, biz = duena
    client.force_login(user)

    assert client.get(f"/reporte/csv/?business={biz.pk}").status_code == 200
    assert client.get(f"/reporte/pdf/?business={biz.pk}").status_code == 200
