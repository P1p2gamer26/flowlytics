"""Configuración que falla temprano: si falta algo de producción, el proceso lo
dice claro en `manage.py check --deploy` en vez de arrancar roto.

Dos niveles, y la diferencia importa: `revisar_config` es lo que impide arrancar
y va como Error, que para el despliegue. `avisos_config` es lo que degrada una
función pero deja el sistema en pie y va como Warning, que se lee y no bloquea.
Meter lo segundo en lo primero es lo que dejó la .28 sin desplegar por una clave
de API opcional.
"""
from django.core.checks import Error, Warning, register


def revisar_config(settings):
    problemas = []
    sk = getattr(settings, "SECRET_KEY", "") or ""
    if not sk or sk.startswith("django-insecure") or sk == "dev-insecure-key":
        problemas.append("SECRET_KEY usa la clave de desarrollo; genera una para producción.")

    if not getattr(settings, "DEBUG", False):
        if not getattr(settings, "DATABASE_URL", ""):
            problemas.append("DATABASE_URL es obligatoria en producción.")
    return problemas


def avisos_config(settings):
    avisos = []
    if getattr(settings, "DEBUG", False):
        return avisos

    if not getattr(settings, "TLS", False):
        avisos.append("Sin TLS: el sitio va por HTTP en claro y las contraseñas del "
                      "login viajan visibles en la red. Sirve para probar desde el "
                      "celular; no pongas un negocio real detrás.")
    if (getattr(settings, "DATABASE_URL", "") or "").startswith("sqlite"):
        avisos.append("DATABASE_URL apunta a SQLite; en producción se espera Postgres.")
    if not getattr(settings, "ANTHROPIC_API_KEY", ""):
        avisos.append("Sin ANTHROPIC_API_KEY: las descripciones de escena quedan "
                      "desactivadas. El resto del sistema funciona igual.")
    if "smtp" not in (getattr(settings, "EMAIL_BACKEND", "") or ""):
        avisos.append("Los avisos por correo se imprimen en el log del servidor: "
                      "nadie los recibe. Configura EMAIL_BACKEND y EMAIL_HOST "
                      "para que lleguen al dueño.")
    return avisos


@register(deploy=True)
def _check_config(app_configs, **kwargs):
    from django.conf import settings
    hallazgos = [Error(m, id=f"config.E{i:03d}")
                 for i, m in enumerate(revisar_config(settings), start=1)]
    hallazgos += [Warning(m, id=f"config.W{i:03d}")
                  for i, m in enumerate(avisos_config(settings), start=1)]
    return hallazgos
