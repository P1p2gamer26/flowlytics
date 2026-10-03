import pytest
from django.contrib.auth.models import User

from tenancy.models import Business, Plan, Profile

URL = "rtsp://10.0.0.5:554/stream1"


@pytest.fixture
def mundo(db):
    plan = Plan.objects.create(nombre="Test", max_camaras=10)
    a = Business.objects.create(name="A", kind="retail", plan=plan)
    b = Business.objects.create(name="B", kind="cafe", plan=plan)
    ana = User.objects.create_user("ana", password="x")
    Profile.objects.create(user=ana, role="owner", business=a)
    return dict(a=a, b=b, ana=ana)


class CapturaFalsa:
    def __init__(self, abierta=True, da_frame=True):
        self._abierta, self._da_frame = abierta, da_frame

    def isOpened(self):
        return self._abierta

    def read(self):
        return (self._da_frame, object() if self._da_frame else None)

    def release(self):
        pass


@pytest.mark.django_db
def test_una_camara_que_conecta_lo_dice(api_client, mundo, monkeypatch):
    import cameras.api as api

    monkeypatch.setattr(api, "_sondear_tcp", lambda host, puerto: True)
    monkeypatch.setattr(api, "_abrir_stream", lambda url: CapturaFalsa())
    api_client.force_authenticate(mundo["ana"])

    r = api_client.post("/api/camaras/probar/",
                        {"business": mundo["a"].pk, "source": URL}, format="json")

    assert r.status_code == 200
    assert r.json()["ok"] is True


@pytest.mark.django_db
def test_una_camara_apagada_explica_que_no_responde(api_client, mundo, monkeypatch):
    import cameras.api as api

    monkeypatch.setattr(api, "_sondear_tcp", lambda host, puerto: False)
    api_client.force_authenticate(mundo["ana"])

    r = api_client.post("/api/camaras/probar/",
                        {"business": mundo["a"].pk, "source": URL}, format="json")

    assert r.status_code == 200
    assert r.json()["ok"] is False
    assert "10.0.0.5:554" in r.json()["mensaje"]


@pytest.mark.django_db
def test_una_direccion_mal_escrita_no_abre_ninguna_conexion(api_client, mundo, monkeypatch):
    import cameras.api as api

    aperturas = []
    monkeypatch.setattr(api, "_sondear_tcp", lambda host, puerto: aperturas.append("tcp") or True)
    monkeypatch.setattr(api, "_abrir_stream", lambda url: aperturas.append("stream") or CapturaFalsa())
    api_client.force_authenticate(mundo["ana"])

    r = api_client.post("/api/camaras/probar/",
                        {"business": mundo["a"].pk, "source": "camara del fondo"},
                        format="json")

    assert r.json()["ok"] is False
    assert aperturas == []


@pytest.mark.django_db
def test_la_prueba_usa_la_contrasena_pero_no_la_devuelve(api_client, mundo, monkeypatch):
    import cameras.api as api

    urls = []
    monkeypatch.setattr(api, "_sondear_tcp", lambda host, puerto: True)
    monkeypatch.setattr(api, "_abrir_stream",
                        lambda url: urls.append(url) or CapturaFalsa())
    api_client.force_authenticate(mundo["ana"])

    r = api_client.post("/api/camaras/probar/",
                        {"business": mundo["a"].pk, "source": URL,
                         "usuario": "admin", "password": "SuperSecreta123"},
                        format="json")

    assert urls == ["rtsp://admin:SuperSecreta123@10.0.0.5:554/stream1"]
    assert "SuperSecreta123" not in r.content.decode()


@pytest.mark.django_db
def test_no_se_prueba_una_camara_para_otro_negocio(api_client, mundo):
    api_client.force_authenticate(mundo["ana"])

    r = api_client.post("/api/camaras/probar/",
                        {"business": mundo["b"].pk, "source": URL}, format="json")

    assert r.status_code == 403
