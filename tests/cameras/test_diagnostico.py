# tests/cameras/test_diagnostico.py
"""Los cuatro fallos de una cámara en vivo, sin cámara y sin red.

`sondear` y `abrir` se inyectan: aquí no se abre un socket ni se llama a FFmpeg.
"""
from cameras.diagnostico import destino, diagnosticar, revisar_direccion

URL = "rtsp://10.0.0.5:554/stream1"


class CapturaFalsa:
    """Doble de cv2.VideoCapture con lo justo que mira el diagnóstico."""

    def __init__(self, abierta=True, da_frame=True):
        self._abierta = abierta
        self._da_frame = da_frame
        self.liberada = False

    def isOpened(self):
        return self._abierta

    def read(self):
        return (self._da_frame, object() if self._da_frame else None)

    def release(self):
        self.liberada = True


def test_una_direccion_vacia_no_llega_a_la_red():
    llamadas = []

    r = diagnosticar("", lambda h, p: llamadas.append((h, p)) or True,
                     lambda: CapturaFalsa())

    assert r["ok"] is False
    assert "rtsp://" in r["mensaje"]
    assert llamadas == []          # ni sondeo ni conexión: no hacía falta


def test_una_direccion_sin_esquema_se_rechaza_sin_tocar_la_red():
    r = diagnosticar("192.168.1.50", lambda h, p: True, lambda: CapturaFalsa())

    assert r["ok"] is False
    assert "empezar por rtsp://" in r["mensaje"]


def test_una_direccion_sin_host_se_rechaza():
    assert "IP" in revisar_direccion("rtsp://")


def test_la_contrasena_dentro_de_la_url_se_manda_a_su_casilla():
    """Pegarla en la URL la guardaría en claro en `source`. Se explica por qué no."""
    aviso = revisar_direccion("rtsp://admin:SuperSecreta123@10.0.0.5:554/stream1")

    assert aviso is not None
    assert "SuperSecreta123" not in aviso
    assert "cifradas" in aviso


def test_una_direccion_buena_no_tiene_nada_que_decir():
    assert revisar_direccion(URL) is None


def test_el_puerto_por_defecto_de_rtsp_es_554():
    assert destino("rtsp://10.0.0.5/stream1") == ("10.0.0.5", 554)
    assert destino("rtsp://10.0.0.5:8554/stream1") == ("10.0.0.5", 8554)


def test_si_el_equipo_no_responde_lo_dice_con_su_ip_y_su_puerto():
    r = diagnosticar(URL, lambda h, p: False, lambda: CapturaFalsa())

    assert r["ok"] is False
    assert "10.0.0.5:554" in r["mensaje"]
    assert "apagada" in r["mensaje"] or "red" in r["mensaje"]


def test_si_responde_pero_no_abre_el_stream_apunta_a_la_contrasena():
    r = diagnosticar(URL, lambda h, p: True, lambda: CapturaFalsa(abierta=False))

    assert r["ok"] is False
    assert "contraseña" in r["mensaje"]


def test_si_abre_pero_no_llega_imagen_apunta_al_codec():
    r = diagnosticar(URL, lambda h, p: True,
                     lambda: CapturaFalsa(da_frame=False))

    assert r["ok"] is False
    assert "H.264" in r["mensaje"]


def test_cuando_todo_va_bien_lo_dice_y_suelta_la_conexion():
    captura = CapturaFalsa()

    r = diagnosticar(URL, lambda h, p: True, lambda: captura)

    assert r["ok"] is True
    assert captura.liberada is True


def test_la_conexion_se_suelta_tambien_cuando_falla():
    """Una sonda que deja el socket abierto acaba comiéndose las conexiones de
    la cámara: casi todas admiten dos o tres a la vez."""
    captura = CapturaFalsa(da_frame=False)

    diagnosticar(URL, lambda h, p: True, lambda: captura)

    assert captura.liberada is True


def test_si_abrir_revienta_se_traduce_en_vez_de_propagarse():
    def abrir():
        raise OSError("Connection refused")

    r = diagnosticar(URL, lambda h, p: True, abrir)

    assert r["ok"] is False
    assert r["mensaje"]