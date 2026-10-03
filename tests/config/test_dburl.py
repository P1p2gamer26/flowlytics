import pytest

from config.dburl import parse_database_url


def test_url_vacia_cae_en_sqlite():
    cfg = parse_database_url("", base_dir="/tmp/proj")
    assert cfg["ENGINE"] == "django.db.backends.sqlite3"
    assert cfg["NAME"].endswith("db.sqlite3")


def test_sqlite_en_memoria():
    cfg = parse_database_url("sqlite://")
    assert cfg["ENGINE"] == "django.db.backends.sqlite3"
    assert cfg["NAME"] == ":memory:"


def test_postgres_se_desarma_en_campos():
    cfg = parse_database_url("postgres://analytics:cl%40ve@localhost:5432/vision")
    assert cfg["ENGINE"] == "django.db.backends.postgresql"
    assert cfg["NAME"] == "vision"
    assert cfg["USER"] == "analytics"
    assert cfg["PASSWORD"] == "cl@ve"        # %40 se decodifica
    assert cfg["HOST"] == "localhost"
    assert cfg["PORT"] == "5432"


def test_esquema_desconocido_falla_temprano():
    with pytest.raises(ValueError):
        parse_database_url("mysql://x/y")


def test_sqlite_espera_si_la_base_esta_ocupada():
    # Varios workers escriben a la vez; sin timeout fallan con "database is locked".
    assert parse_database_url("sqlite:///db.sqlite3")["OPTIONS"]["timeout"] >= 10
    assert parse_database_url("", ".")["OPTIONS"]["timeout"] >= 10
