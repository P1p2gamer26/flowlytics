from types import SimpleNamespace

from config.validate import avisos_config, revisar_config


def _settings(**kw):
    base = dict(SECRET_KEY="una-clave-larga-de-produccion", DEBUG=False, TLS=True,
                DATABASE_URL="postgres://u:p@h/db", ANTHROPIC_API_KEY="sk-real",
                EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend")
    base.update(kw)
    return SimpleNamespace(**base)


def test_config_de_produccion_valida_no_reporta_nada():
    assert revisar_config(_settings()) == []
    assert avisos_config(_settings()) == []


def test_secret_key_de_desarrollo_se_reporta():
    problemas = revisar_config(_settings(SECRET_KEY="django-insecure-xyz"))
    assert any("SECRET_KEY" in p for p in problemas)


def test_database_url_obligatoria_en_produccion():
    problemas = revisar_config(_settings(DATABASE_URL=""))
    assert any("DATABASE_URL" in p for p in problemas)


def test_en_debug_no_exige_secretos_de_produccion():
    # desarrollo local: DEBUG=True, sin DB ni clave real, no debe estorbar
    assert revisar_config(_settings(DEBUG=True, DATABASE_URL="", ANTHROPIC_API_KEY="")) == []
    assert avisos_config(_settings(DEBUG=True, TLS=False)) == []


def test_sin_anthropic_key_es_aviso_y_no_error():
    # el sistema funciona sin ella: solo se apagan las descripciones de escena.
    # Que un secreto opcional bloquee el despliegue es lo que dejó la .28 sin correr.
    sin_key = _settings(ANTHROPIC_API_KEY="")
    assert revisar_config(sin_key) == []
    assert any("ANTHROPIC_API_KEY" in a for a in avisos_config(sin_key))


def test_sin_tls_se_avisa_pero_no_se_bloquea():
    sin_tls = _settings(TLS=False)
    assert revisar_config(sin_tls) == []
    avisos = avisos_config(sin_tls)
    assert any("HTTP en claro" in a for a in avisos)
    assert any("negocio real" in a for a in avisos)


def test_sqlite_en_produccion_es_aviso():
    avisos = avisos_config(_settings(DATABASE_URL="sqlite:///db.sqlite3"))
    assert any("SQLite" in a for a in avisos)


def test_avisa_si_el_correo_solo_va_al_log():
    avisos = avisos_config(_settings(
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend"))

    assert any("correo" in a for a in avisos)


def test_con_smtp_configurado_no_avisa_del_correo():
    avisos = avisos_config(_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend"))

    assert not any("correo" in a for a in avisos)
