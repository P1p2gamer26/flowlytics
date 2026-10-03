from django.core.exceptions import PermissionDenied

from .models import Business


def business_or_403(user, business_id):
    """Devuelve el Business si el usuario puede verlo; si no, 403.

    Punto único de control de acceso por tenant: toda vista pasa por aquí.
    """
    business = Business.objects.for_user(user).filter(pk=business_id).first()
    if business is None:
        raise PermissionDenied("No tienes acceso a este negocio.")
    return business
