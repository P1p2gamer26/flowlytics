import logging

from config.logging_filters import RedactorDeCredenciales, redactar


def test_redacta_password_de_url_rtsp():
    salida = redactar("conectando a rtsp://admin:SuperSecreta123@10.0.0.5:554/stream")
    assert "SuperSecreta123" not in salida
    assert "rtsp://admin:***@10.0.0.5:554/stream" in salida


def test_texto_sin_credenciales_no_cambia():
    assert redactar("todo bien, 120 frames") == "todo bien, 120 frames"


def test_el_filtro_redacta_el_record():
    filtro = RedactorDeCredenciales()
    record = logging.LogRecord("x", logging.INFO, __file__, 1,
                               "fuente %s caida", ("rtsp://u:p4ssw0rd@h/s",), None)
    filtro.filter(record)

    assert "p4ssw0rd" not in record.getMessage()
