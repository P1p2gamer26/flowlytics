"""Reglas y avisos de ejemplo de HOY para la demo. Idempotente: borra lo previo del negocio."""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from cameras.models import Camera

from .models import AlertDelivery, AlertRule

REGLAS = [
    dict(tipo_evento="long_queue", umbral=240, accion="avisar", canal="email",
         destino="dueno@mitienda.co"),
    dict(tipo_evento="empty_counter", umbral=1, accion="mensaje_personal",
         texto="Hay una caja sola: que alguien vuelva al mostrador"),
    dict(tipo_evento="overcrowding", umbral=25, accion="abrir_caja"),
]

# (tipo, minutos atrás, resultado, mensaje)
AVISOS = [
    ("long_queue", 12, "enviada", "Fila larga en Fila de caja: 5 min de espera"),
    ("overcrowding", 35, "registrada", "Pedir a un empleado que abra la segunda caja — Aforo excedido en Sala"),
    ("empty_counter", 58, "registrada", "Hay una caja sola: que alguien vuelva al mostrador — Caja desatendida en Caja 1"),
    ("long_queue", 95, "enviada", "Fila larga en Fila de caja: 6 min de espera"),
    ("long_queue", 101, "silenciada", "Fila larga en Fila de caja: 6 min de espera"),
    ("overcrowding", 160, "registrada", "Pedir a un empleado que abra la segunda caja — Aforo excedido en Sala"),
    ("empty_counter", 230, "registrada", "Hay una caja sola: que alguien vuelva al mostrador — Caja desatendida en Caja 1"),
    ("long_queue", 290, "enviada", "Fila larga en Fila de caja: 4 min de espera"),
]


@transaction.atomic
def sembrar_avisos(business):
    camara = Camera.objects.filter(business=business).first()
    nombre_camara = camara.name if camara else "Cámara demo"
    AlertRule.objects.filter(business=business).delete()   # borra también sus entregas
    reglas = {d["tipo_evento"]: AlertRule.objects.create(business=business, **d) for d in REGLAS}
    ahora = timezone.now()
    for tipo, minutos, resultado, mensaje in AVISOS:
        entrega = AlertDelivery.objects.create(rule=reglas[tipo], mensaje=mensaje,
                                               resultado=resultado, camara=nombre_camara)
        # auto_now_add ignora el valor al crear: se fija después.
        AlertDelivery.objects.filter(pk=entrega.pk).update(creado=ahora - timedelta(minutes=minutos))
