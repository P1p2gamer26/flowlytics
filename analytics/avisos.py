"""Con qué umbral avisa cada negocio.

Dos fuentes y un orden claro: el rubro pone el suelo (`tenancy/rubros.py`, la
misma tabla que decide qué cifras ve cada tipo de local) y las reglas del
negocio lo pisan cuando el dueño toca el número desde el panel.

`activa` no se mira aquí a propósito: eso decide si se manda el aviso
(`notificar_evento`), no si se detecta el evento. Mezclarlo dejaría al negocio
sin historial en cuanto alguien silencia una alerta.
"""
from tenancy.rubros import perfil
from vision.core.events import reglas_desde

from .models import AlertRule


def umbrales_de(business):
    umbrales = dict(perfil(business.kind)["avisos"])
    for regla in AlertRule.objects.filter(business=business).exclude(umbral=None):
        umbrales[regla.tipo_evento] = regla.umbral
    return umbrales


def reglas_de(business):
    """Las reglas que `Pipeline` recibe hoy como `DEFAULT_RULES`, pero de este negocio."""
    return reglas_desde(umbrales_de(business))
