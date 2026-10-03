# config/entorno.py
"""Lo que cambia entre esta VM y una máquina con certificado, en un solo sitio.

La .28 no tiene TLS. Forzar HTTPS ahí deja el panel inalcanzable desde el celular
—301 a un puerto 443 que nadie escucha— y, peor, el HSTS se graba en el navegador
por un año y no se deshace apagando el setting. Por eso tener certificado es una
decisión explícita (DJANGO_TLS), no algo que se deduzca de DEBUG.
"""

# Las dos VMs del curso. Se sobreescriben con DJANGO_ALLOWED_HOSTS.
HOSTS_POR_DEFECTO = ("localhost", "127.0.0.1")


def hosts_permitidos(valor, por_defecto=HOSTS_POR_DEFECTO):
    """Lista separada por comas; vacía o ausente cae en los hosts conocidos."""
    hosts = [h.strip() for h in (valor or "").split(",") if h.strip()]
    return hosts or list(por_defecto)


def ajustes_tls(tls, hosts):
    """Los settings de seguridad que dependen de si hay certificado o no.

    Sin TLS se apagan las cookies Secure (si no, no hay login por HTTP), la
    redirección y el HSTS. No es "seguridad desactivada": es no fingir que hay
    HTTPS. Lo que eso implica lo dice avisos_config y lo repite el README.
    """
    if not tls:
        return {
            "SESSION_COOKIE_SECURE": False,
            "CSRF_COOKIE_SECURE": False,
            "SECURE_SSL_REDIRECT": False,
            "SECURE_HSTS_SECONDS": 0,
            "CSRF_TRUSTED_ORIGINS": [f"http://{h}" for h in hosts],
        }
    return {
        "SESSION_COOKIE_SECURE": True,
        "CSRF_COOKIE_SECURE": True,
        "SECURE_SSL_REDIRECT": True,
        "SECURE_PROXY_SSL_HEADER": ("HTTP_X_FORWARDED_PROTO", "https"),
        "SECURE_HSTS_SECONDS": 31536000,
        "SECURE_HSTS_INCLUDE_SUBDOMAINS": True,
        "SECURE_HSTS_PRELOAD": True,
        "CSRF_TRUSTED_ORIGINS": [f"https://{h}" for h in hosts],
    }
