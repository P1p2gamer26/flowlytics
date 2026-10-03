"""collectstatic es un paso de deploy.sh: sin STATIC_ROOT revienta el despliegue."""
from django.conf import settings
from django.core.management import call_command


def test_static_root_configurado_y_collectstatic_no_revienta():
    assert settings.STATIC_ROOT, "sin STATIC_ROOT, collectstatic falla en deploy.sh"
    assert str(settings.STATIC_ROOT).endswith("staticfiles")

    # --dry-run no escribe nada, pero sí exige que STATIC_ROOT esté puesto
    call_command("collectstatic", "--noinput", "--dry-run", verbosity=0)
