"""Modo demo local: si SIN_CUENTA=1, cualquier visitante entra como admin 'demo'."""
from django.conf import settings
from django.contrib.auth import get_user_model, login


def sin_cuenta(get_response):
    def middleware(request):
        if settings.SIN_CUENTA and not request.user.is_authenticated:
            from tenancy.models import Profile
            user, _ = get_user_model().objects.get_or_create(
                username="demo", defaults={"is_staff": True, "is_superuser": True})
            Profile.objects.update_or_create(user=user, defaults={"role": "admin", "business": None})
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return get_response(request)
    return middleware
