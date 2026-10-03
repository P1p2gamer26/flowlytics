import numpy as np
import pytest

from vision.core.source import FrameSource, FuenteFalsa


def frame(v=1):
    return np.full((4, 4, 3), v, dtype=np.uint8)


def test_lee_frames_en_orden():
    fuente = FuenteFalsa([frame(1), frame(2)])
    src = FrameSource(abrir=lambda: fuente, dormir=lambda s: None)

    assert int(src.leer()[0, 0, 0]) == 1
    assert int(src.leer()[0, 0, 0]) == 2


def test_reconecta_cuando_la_lectura_falla():
    intentos = []

    def abrir():
        intentos.append(1)
        # la primera fuente falla al segundo frame; la segunda funciona
        return FuenteFalsa([frame(1), None]) if len(intentos) == 1 else FuenteFalsa([frame(9)])

    src = FrameSource(abrir=abrir, dormir=lambda s: None)

    assert int(src.leer()[0, 0, 0]) == 1
    assert int(src.leer()[0, 0, 0]) == 9
    assert src.reconexiones == 1


def test_se_rinde_tras_agotar_los_reintentos():
    src = FrameSource(abrir=lambda: FuenteFalsa([None]),
                      max_reintentos=3, dormir=lambda s: None)

    assert src.leer() is None
    assert src.cerrada is True
    assert src.reconexiones == 3


def test_el_backoff_es_exponencial_y_acotado():
    esperas = []
    src = FrameSource(abrir=lambda: FuenteFalsa([None]), max_reintentos=5,
                      backoff_base=2.0, dormir=esperas.append)

    src.leer()

    assert esperas == [2.0, 4.0, 8.0, 16.0, 30.0]   # tope de 30 s


def test_reconexion_exitosa_reinicia_el_backoff():
    intentos = []

    def abrir():
        intentos.append(1)
        if len(intentos) == 1:
            return FuenteFalsa([None])
        if len(intentos) == 2:
            return FuenteFalsa([frame(5), None])
        return FuenteFalsa([frame(7)])

    esperas = []
    src = FrameSource(abrir=abrir, dormir=esperas.append)

    assert int(src.leer()[0, 0, 0]) == 5
    assert int(src.leer()[0, 0, 0]) == 7
    assert esperas == [2.0, 2.0]   # el segundo fallo vuelve a empezar en 2 s


def test_si_abrir_lanza_excepcion_tambien_reintenta():
    intentos = []

    def abrir():
        intentos.append(1)
        if len(intentos) == 1:
            raise OSError("no se pudo conectar")
        return FuenteFalsa([frame(3)])

    src = FrameSource(abrir=abrir, dormir=lambda s: None)

    assert int(src.leer()[0, 0, 0]) == 3


from vision.core.source import BACKOFF_MAX


def test_una_camara_en_vivo_no_se_rinde_nunca():
    """max_reintentos=None: veinte fallos seguidos y sigue esperando."""
    intentos = []

    def abrir():
        intentos.append(1)
        return FuenteFalsa([frame(4)]) if len(intentos) > 20 else FuenteFalsa([None])

    src = FrameSource(abrir=abrir, max_reintentos=None, dormir=lambda s: None)

    assert int(src.leer()[0, 0, 0]) == 4
    assert src.cerrada is False
    assert src.reconexiones == 20


def test_sin_tope_de_reintentos_la_espera_sigue_acotada():
    """Reintentar para siempre no puede volverse esperar para siempre."""
    esperas = []

    def abrir():
        return FuenteFalsa([frame(1)]) if len(esperas) >= 12 else FuenteFalsa([None])

    src = FrameSource(abrir=abrir, max_reintentos=None, dormir=esperas.append)
    src.leer()

    assert esperas[:3] == [2.0, 4.0, 8.0]
    assert max(esperas) == BACKOFF_MAX
    assert esperas[-1] == BACKOFF_MAX


def test_avisa_de_cada_reconexion_con_su_motivo():
    """Sin este aviso la cámara caída es una cámara muda: nadie sabe qué pasa."""
    avisos = []

    def abrir():
        if not avisos:
            raise OSError("no route to host")
        return FuenteFalsa([frame(2)])

    src = FrameSource(abrir=abrir, dormir=lambda s: None,
                      al_reconectar=lambda n, espera, motivo: avisos.append((n, espera, motivo)))
    src.leer()

    assert avisos == [(1, 2.0, "no route to host")]


def test_el_motivo_no_filtra_la_contrasena():
    motivos = []

    def abrir():
        if not motivos:
            raise OSError("open failed rtsp://admin:SuperSecreta123@10.0.0.5:554/stream")
        return FuenteFalsa([frame(1)])

    src = FrameSource(abrir=abrir, dormir=lambda s: None,
                      al_reconectar=lambda n, e, motivo: motivos.append(motivo))
    src.leer()

    assert "SuperSecreta123" not in motivos[0]
    assert "rtsp://admin:***@10.0.0.5:554/stream" in motivos[0]


def test_un_archivo_sigue_terminando_cuando_se_acaba():
    """La fuente de archivo no cambia: reintentar un video agotado es un bucle."""
    src = FrameSource(abrir=lambda: FuenteFalsa([frame(1)]), es_archivo=True,
                      captura_inicial=FuenteFalsa([frame(1)]), dormir=lambda s: None)

    assert src.leer() is not None
    assert src.leer() is None
    assert src.cerrada is True
