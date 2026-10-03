# tests/config/test_entorno.py
"""Lo que cambia entre un servidor sin certificado y una máquina de verdad.

Sin esto, DEBUG=False forzaba HTTPS en una máquina sin TLS: el panel quedaba
inalcanzable desde el celular y el HSTS se grababa por un año.
"""
from config.entorno import ajustes_tls, hosts_permitidos


def test_sin_variable_solo_se_sirve_en_local():
    assert hosts_permitidos("") == ["localhost", "127.0.0.1"]


def test_la_variable_manda_y_se_limpian_los_espacios():
    assert hosts_permitidos(" panel.local , 10.0.0.9 ") == ["panel.local", "10.0.0.9"]


def test_sin_tls_no_se_redirige_ni_se_graba_hsts():
    ajustes = ajustes_tls(False, ["192.168.1.50"])

    assert ajustes["SECURE_SSL_REDIRECT"] is False
    assert ajustes["SECURE_HSTS_SECONDS"] == 0        # un año de HSTS no se deshace
    assert ajustes["SESSION_COOKIE_SECURE"] is False  # si no, no habría login por HTTP
    assert ajustes["CSRF_TRUSTED_ORIGINS"] == ["http://192.168.1.50"]


def test_con_tls_se_enciende_todo_lo_de_siempre():
    ajustes = ajustes_tls(True, ["panel.local"])

    assert ajustes["SECURE_SSL_REDIRECT"] is True
    assert ajustes["SECURE_HSTS_SECONDS"] == 31536000
    assert ajustes["SESSION_COOKIE_SECURE"] is True
    assert ajustes["CSRF_COOKIE_SECURE"] is True
    assert ajustes["SECURE_PROXY_SSL_HEADER"] == ("HTTP_X_FORWARDED_PROTO", "https")
    assert ajustes["CSRF_TRUSTED_ORIGINS"] == ["https://panel.local"]
