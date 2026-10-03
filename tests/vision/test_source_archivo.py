import numpy as np

from vision.core.source import (
    FrameSource,
    FuenteFalsa,
    es_fuente_archivo,
    ruta_archivo,
)


def frame(v=1):
    return np.full((4, 4, 3), v, dtype=np.uint8)


def test_detecta_archivos_por_prefijo_file():
    assert es_fuente_archivo("file://demo/videos/x.mp4") is True
    assert es_fuente_archivo("0") is False
    assert es_fuente_archivo("rtsp://10.0.0.5:554/stream") is False
    assert es_fuente_archivo("http://10.0.0.5/x.mp4") is False


def test_detecta_ruta_que_existe_en_disco(tmp_path):
    video = tmp_path / "x.mp4"
    video.write_bytes(b"")
    assert es_fuente_archivo(str(video)) is True


def test_ruta_archivo_quita_el_prefijo():
    assert ruta_archivo("file://demo/videos/x.mp4") == "demo/videos/x.mp4"


def test_ruta_archivo_deja_la_ruta_desnuda():
    assert ruta_archivo("demo/videos/x.mp4") == "demo/videos/x.mp4"


def test_lee_todo_el_archivo_y_luego_se_cierra():
    src = FrameSource(abrir=lambda: FuenteFalsa([frame(1), frame(2)]),
                      es_archivo=True, loop=False)

    assert int(src.leer()[0, 0, 0]) == 1
    assert src.fps_archivo == 2.0
    assert src.ancho == 4
    assert int(src.leer()[0, 0, 0]) == 2
    assert src.leer() is None
    assert src.cerrada is True


def test_archivo_con_loop_se_rebobina_sin_reabrir():
    intentos = []

    def abrir():
        intentos.append(1)
        return FuenteFalsa([frame(1), frame(2)])

    src = FrameSource(abrir=abrir, es_archivo=True, loop=True)

    valores = []
    for _ in range(6):
        f = src.leer()
        if f is None:
            break
        valores.append(int(f[0, 0, 0]))

    assert valores == [1, 2, 1, 2, 1, 2]
    assert src.cerrada is False
    assert len(intentos) == 1


def test_archivo_que_no_abre_falla_limpio_sin_reintentos():
    src = FrameSource(abrir=lambda: None, es_archivo=True, loop=True)

    assert src.leer() is None
    assert src.cerrada is True
    assert src.reconexiones == 0
