"""El verificador se prueba con dobles: ni red ni systemd ni Postgres.

`lector_salud` y `estado_unidad` se inyectan justamente para esto, igual que el
executor de sync_workers.
"""
import pytest
from django.core.management import CommandError, call_command

from cameras.models import Camera, CameraHealth
from dashboard.verificacion import formatear, verificar
from tenancy.models import Business


def salud_ok():
    return {"db": True, "version": "prueba", "workers": [], "jobs": {}}


def salud_caida():
    raise OSError("connection refused")


@pytest.fixture
def prod(settings, tmp_path):
    """Settings como los de la .28 ya desplegada, pero con SQLite y /tmp."""
    settings.SECRET_KEY = "una-clave-larga-de-produccion"
    settings.DEBUG = False
    settings.TLS = False
    settings.DATABASE_URL = "postgres://u:p@localhost/vision"
    settings.ANTHROPIC_API_KEY = "sk-real"
    settings.STATIC_ROOT = str(tmp_path / "staticfiles")
    (tmp_path / "staticfiles").mkdir()
    (tmp_path / "staticfiles" / "app.css").write_text("body{}")
    return settings


def _por_nombre(chequeos):
    return {c.nombre: c for c in chequeos}


@pytest.mark.django_db
def test_un_despliegue_sano_no_deja_ningun_critico_en_rojo(prod):
    chequeos = verificar(salud_ok, lambda unidad: "active")

    assert [c.nombre for c in chequeos if not c.ok and c.critico] == []
    assert _por_nombre(chequeos)["migraciones"].ok is True


@pytest.mark.django_db
def test_si_la_web_no_responde_es_critico_y_lo_dice(prod):
    chequeos = _por_nombre(verificar(salud_caida, lambda unidad: "active"))

    assert chequeos["web"].ok is False
    assert chequeos["web"].critico is True
    assert "connection refused" in chequeos["web"].detalle


@pytest.mark.django_db
def test_sin_systemd_se_informa_pero_no_es_critico(prod):
    chequeos = _por_nombre(verificar(salud_ok, lambda unidad: "sin systemd"))

    assert chequeos["unidad web"].ok is False
    assert chequeos["unidad web"].critico is False


@pytest.mark.django_db
def test_los_estaticos_sin_recolectar_son_criticos_en_produccion(prod, tmp_path):
    prod.STATIC_ROOT = str(tmp_path / "vacio")

    chequeo = _por_nombre(verificar(salud_ok, lambda u: "active"))["estáticos"]

    assert chequeo.ok is False and chequeo.critico is True
    assert "collectstatic" in chequeo.detalle


@pytest.mark.django_db
def test_una_camara_habilitada_sin_latido_se_reporta(prod):
    biz = Business.objects.create(name="Cafe", kind="cafe")
    Camera.objects.create(business=biz, name="Barra", source="0", enabled=True)

    chequeo = _por_nombre(verificar(salud_ok, lambda u: "active"))["cámaras"]

    assert chequeo.ok is False
    assert chequeo.critico is False        # el sitio abre igual; el worker se arranca aparte
    assert "0/1" in chequeo.detalle


@pytest.mark.django_db
def test_una_camara_con_latido_fresco_pasa(prod):
    biz = Business.objects.create(name="Cafe", kind="cafe")
    cam = Camera.objects.create(business=biz, name="Barra", source="0", enabled=True)
    CameraHealth.latir(cam, frames=10, reconexiones=0)

    assert _por_nombre(verificar(salud_ok, lambda u: "active"))["cámaras"].ok is True


@pytest.mark.django_db
def test_el_aviso_de_sin_tls_llega_al_informe(prod):
    detalle = _por_nombre(verificar(salud_ok, lambda u: "active"))["configuración"].detalle

    assert "HTTP en claro" in detalle


@pytest.mark.django_db
def test_formatear_marca_lo_bueno_y_lo_malo(prod):
    texto = formatear(verificar(salud_caida, lambda u: "active"))

    assert "✗ web" in texto
    assert "✓ base" in texto
    assert "crítico" in texto


@pytest.mark.django_db
def test_el_comando_falla_cuando_algo_critico_esta_mal(prod, monkeypatch):
    import dashboard.management.commands.verificar as cmd
    monkeypatch.setattr(cmd, "leer_salud", lambda url: salud_caida())
    monkeypatch.setattr(cmd, "estado_unidad", lambda unidad: "active")

    with pytest.raises(CommandError, match="web"):
        call_command("verificar", verbosity=0)


@pytest.mark.django_db
def test_el_comando_pasa_cuando_todo_esta_bien(prod, monkeypatch, capsys):
    import dashboard.management.commands.verificar as cmd
    monkeypatch.setattr(cmd, "leer_salud", lambda url: salud_ok())
    monkeypatch.setattr(cmd, "estado_unidad", lambda unidad: "active")

    call_command("verificar")

    assert "✓ base" in capsys.readouterr().out
