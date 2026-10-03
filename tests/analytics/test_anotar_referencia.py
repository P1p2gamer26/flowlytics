"""El comando de anotación. No abre video: `sondear` se sustituye por un doble."""
import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from analytics.management.commands import anotar_referencia as cmd_mod

SONDEO = {"ancho": 1280, "alto": 720, "fps": 30.0, "frames": 900,
          "duracion_s": 30.0, "h264": True}


@pytest.fixture
def referencia(tmp_path):
    ruta = tmp_path / "referencia.json"
    ruta.write_text(json.dumps({"videos": []}))
    return ruta


@pytest.fixture(autouse=True)
def sin_opencv(monkeypatch):
    monkeypatch.setattr(cmd_mod, "sondear", lambda ruta: dict(SONDEO))


def test_toma_del_video_las_claves_que_escalan_la_linea(tmp_path, referencia):
    video = tmp_path / "tienda" / "entrada.mp4"
    video.parent.mkdir()
    video.write_bytes(b"no importa: sondear es un doble")

    call_command("anotar_referencia", str(video), "--referencia", str(referencia),
                 "--ruta", "tienda/entrada.mp4", verbosity=0)

    entrada = json.loads(referencia.read_text())["videos"][0]
    assert entrada["ruta"] == "tienda/entrada.mp4"
    assert (entrada["ancho"], entrada["alto"], entrada["fps"]) == (1280, 720, 30.0)
    assert entrada["duracion_s"] == 30.0
    assert entrada["entradas"] is None      # el conteo a mano no lo inventa nadie


def test_las_banderas_de_conteo_llenan_la_anotacion(tmp_path, referencia):
    video = tmp_path / "a.mp4"
    video.write_bytes(b"x")

    call_command("anotar_referencia", str(video), "--referencia", str(referencia),
                 "--ruta", "tienda/a.mp4", "--entradas", "37", "--salidas", "35",
                 "--aforo-max", "6", "--contexto", "tienda", verbosity=0)

    entrada = json.loads(referencia.read_text())["videos"][0]
    assert (entrada["entradas"], entrada["salidas"], entrada["aforo_max"]) == (37, 35, 6)
    assert entrada["contexto"] == "tienda"


def test_reanotar_el_mismo_video_no_lo_duplica(tmp_path, referencia):
    video = tmp_path / "a.mp4"
    video.write_bytes(b"x")
    argumentos = [str(video), "--referencia", str(referencia), "--ruta", "tienda/a.mp4"]

    call_command("anotar_referencia", *argumentos, "--entradas", "10", verbosity=0)
    call_command("anotar_referencia", *argumentos, "--entradas", "12", verbosity=0)

    videos = json.loads(referencia.read_text())["videos"]
    assert len(videos) == 1 and videos[0]["entradas"] == 12


def test_un_video_que_no_existe_lo_dice_antes_de_tocar_la_referencia(tmp_path, referencia):
    antes = referencia.read_text()
    with pytest.raises(CommandError, match="No existe"):
        call_command("anotar_referencia", str(tmp_path / "fantasma.mp4"),
                     "--referencia", str(referencia), verbosity=0)
    assert referencia.read_text() == antes


def test_avisa_cuando_el_video_no_es_reproducible_en_el_navegador(tmp_path, referencia,
                                                                  monkeypatch, capsys):
    monkeypatch.setattr(cmd_mod, "sondear", lambda ruta: {**SONDEO, "h264": False})
    video = tmp_path / "a.mp4"
    video.write_bytes(b"x")

    call_command("anotar_referencia", str(video), "--referencia", str(referencia),
                 "--ruta", "tienda/a.mp4")

    assert "h264" in capsys.readouterr().out.lower()
