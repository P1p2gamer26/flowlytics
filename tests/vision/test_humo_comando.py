"""El comando de humo, con dobles: la suite no abre video ni carga YOLO."""
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from analytics.models import MetricWindow
from cameras.models import Camera
from vision.management.commands import humo as cmd

VIDEO = {"ancho": 32, "alto": 24, "fps": 2.0, "frames": 4,
         "duracion_s": 2.0, "h264": True}


@pytest.fixture
def archivo(tmp_path):
    ruta = tmp_path / "local.mp4"
    ruta.write_bytes(b"da igual: sondear va con doble")
    return ruta


def _dobles(monkeypatch, poligono=None, muestras=0, analizar=None, video=None):
    monkeypatch.setattr(cmd, "sondear", lambda ruta: dict(video or VIDEO))
    monkeypatch.setattr(cmd, "sugerir", lambda camera, segundos: (poligono, muestras))
    monkeypatch.setattr(cmd, "analizar", analizar or (lambda camera, segundos, window: None))


def _una_ventana(camera, segundos, window):
    ahora = timezone.now()
    MetricWindow.objects.create(camera=camera, zone_name="sugerida", zone_kind="general",
                                started_at=ahora, ended_at=ahora, occupancy_avg=2.0,
                                occupancy_max=3, dwell_seconds=12.0, unique_visitors=5)


@pytest.mark.django_db
def test_humo_corre_el_ciclo_y_escribe_el_informe(archivo, tmp_path, monkeypatch):
    _dobles(monkeypatch, poligono=[[0, 0], [32, 0], [32, 24]], muestras=41,
            analizar=_una_ventana)
    salida = tmp_path / "informe.md"

    call_command("humo", str(archivo), "--salida", str(salida), verbosity=0)

    camera = Camera.objects.get()
    assert camera.frame_w == 32 and camera.frame_h == 24
    assert camera.source == f"file://{archivo}"
    assert camera.zones.count() == 1
    texto = salida.read_text(encoding="utf-8")
    assert "Ventanas cerradas: **1**" in texto
    assert "41 detecciones" in texto
    assert "Visitantes únicos del día: **5**" in texto


@pytest.mark.django_db
def test_sin_sugerencia_usa_el_frame_completo_y_lo_avisa(archivo, tmp_path, monkeypatch):
    _dobles(monkeypatch, poligono=None, muestras=3, analizar=_una_ventana)
    salida = tmp_path / "informe.md"

    call_command("humo", str(archivo), "--salida", str(salida), verbosity=0)

    zona = Camera.objects.get().zones.get()
    assert zona.polygon == [[0, 0], [32, 0], [32, 24], [0, 24]]
    assert "frame completo" in salida.read_text(encoding="utf-8")


@pytest.mark.django_db
def test_avisa_si_el_video_no_lo_reproduce_el_navegador(archivo, tmp_path, monkeypatch):
    _dobles(monkeypatch, poligono=[[0, 0], [32, 0], [32, 24]], video={**VIDEO, "h264": False})
    salida = tmp_path / "informe.md"

    call_command("humo", str(archivo), "--salida", str(salida), verbosity=0)

    assert "no es H.264" in salida.read_text(encoding="utf-8")


@pytest.mark.django_db
def test_si_el_analisis_se_cae_el_informe_igual_se_escribe(archivo, tmp_path, monkeypatch):
    def revienta(camera, segundos, window):
        raise RuntimeError("el worker murió")

    _dobles(monkeypatch, poligono=[[0, 0], [32, 0], [32, 24]], analizar=revienta)
    salida = tmp_path / "informe.md"

    call_command("humo", str(archivo), "--salida", str(salida), verbosity=0)

    texto = salida.read_text(encoding="utf-8")
    assert "el worker murió" in texto
    assert "No se cerró ninguna ventana" in texto


@pytest.mark.django_db
def test_un_archivo_que_no_existe_se_dice_claro(tmp_path, monkeypatch):
    _dobles(monkeypatch)

    with pytest.raises(CommandError, match="No existe"):
        call_command("humo", str(tmp_path / "fantasma.mp4"), verbosity=0)


@pytest.mark.django_db
def test_dos_pasadas_reusan_el_negocio(archivo, tmp_path, monkeypatch):
    from tenancy.models import Business

    _dobles(monkeypatch, poligono=[[0, 0], [32, 0], [32, 24]])
    call_command("humo", str(archivo), "--salida", str(tmp_path / "a.md"), verbosity=0)
    call_command("humo", str(archivo), "--salida", str(tmp_path / "b.md"), verbosity=0)

    assert Business.objects.filter(name="Humo").count() == 1
    assert Camera.objects.count() == 2


@pytest.mark.django_db
def test_humo_comparar_fps_escribe_seccion_de_estabilidad(archivo, tmp_path, monkeypatch):
    from django.conf import settings

    pasadas = []

    def analizar_mock(camera, segundos, window):
        fps_actual = settings.SAMPLE_FPS
        pasadas.append(fps_actual)
        visitantes = 40 if fps_actual == 2 else 44
        ahora = timezone.now()
        MetricWindow.objects.create(camera=camera, zone_name="sugerida", zone_kind="general",
                                    started_at=ahora, ended_at=ahora, occupancy_avg=2.0,
                                    occupancy_max=3, dwell_seconds=12.0, unique_visitors=visitantes)

    _dobles(monkeypatch, poligono=[[0, 0], [32, 0], [32, 24]], muestras=41,
            analizar=analizar_mock)
    salida = tmp_path / "informe.md"

    call_command("humo", str(archivo), "--comparar-fps", "2,6", "--salida", str(salida), verbosity=0)

    assert pasadas == [2.0, 6.0]
    texto = salida.read_text(encoding="utf-8")
    assert "## Estabilidad del conteo" in texto
    assert "| 2 | 40 |" in texto
    assert "| 6 | 44 |" in texto
    assert "Desvío: 10.0 % — dentro de la tolerancia del 25 %." in texto

