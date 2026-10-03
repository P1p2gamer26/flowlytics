"""Settings de pruebas: SQLite en memoria pase lo que pase en .env.

Garantiza la regla de Fase 4: ningún test toca Postgres.
"""
from config.settings import *  # noqa: F401,F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

# Ninguna prueba abre una conexión SMTP, pase lo que pase en .env: misma regla
# que la de Postgres.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Los tests de "pide login" necesitan que el bypass de la rama sin-cuenta este apagado.
SIN_CUENTA = False
