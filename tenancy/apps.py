from django.apps import AppConfig


class TenancyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tenancy'

    def ready(self):
        import config.validate  # noqa: F401  registra el check --deploy

        from django.contrib.auth import signals
        from django.dispatch import receiver

        from tenancy.models import IntentoLogin

        @receiver(signals.user_login_failed)
        def _fallo(sender, credentials, request=None, **kw):
            IntentoLogin.objects.create(
                identificador=credentials.get("username", ""),
                ip=request.META.get("REMOTE_ADDR") if request else None, exito=False)

        @receiver(signals.user_logged_in)
        def _exito(sender, user, request=None, **kw):
            IntentoLogin.objects.create(
                identificador=user.get_username(),
                ip=request.META.get("REMOTE_ADDR") if request else None, exito=True)
