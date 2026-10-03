"""Traduce DATABASE_URL al dict DATABASES de Django.

Postgres en producción; SQLite (vacío o sqlite://) en tests y desarrollo local,
que es donde su simplicidad gana. Un esquema no soportado falla temprano en vez
de arrancar contra la base equivocada.
"""
from pathlib import Path
from urllib.parse import unquote, urlparse


# Varios workers de camara + el panel escriben a la vez. timeout solo no basta:
# dos transacciones que leen y luego escriben se bloquean mutuamente y SQLite
# devuelve "database is locked" sin esperar. IMMEDIATE toma el candado de
# escritura al empezar (y entonces si espera) y WAL deja leer mientras se escribe.
SQLITE_OPTS = {
    "timeout": 30,
    "transaction_mode": "IMMEDIATE",
    "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
}


def parse_database_url(url, base_dir=None):
    if not url:
        base = Path(base_dir) if base_dir else Path(".")
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": str(base / "db.sqlite3"), "OPTIONS": SQLITE_OPTS}

    p = urlparse(url)
    if p.scheme in ("sqlite", "sqlite3"):
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": p.path.lstrip("/") or ":memory:", "OPTIONS": SQLITE_OPTS}
    if p.scheme in ("postgres", "postgresql"):
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": p.path.lstrip("/"),
            "USER": unquote(p.username or ""),
            "PASSWORD": unquote(p.password or ""),
            "HOST": p.hostname or "",
            "PORT": str(p.port or ""),
        }
    raise ValueError(f"Esquema de base no soportado: {p.scheme!r}")
