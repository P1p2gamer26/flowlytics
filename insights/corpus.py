"""Anonimato y agregados del corpus comparativo.

Toda la lógica con consecuencias de privacidad vive aquí, para que se pueda
auditar leyendo un solo archivo.
"""
import hashlib

from django.conf import settings

# Cohorte mínima para devolver cualquier comparativa. Con menos negocios, un
# "promedio" es reconstruible y equivale a filtrar datos de un cliente a otro.
MIN_COHORTE = 5


def hash_negocio(business) -> str:
    """Huella estable y no reversible de un negocio.

    Permite excluir a un negocio de su propia cohorte sin guardar su id en el
    corpus. Va salteado con SECRET_KEY para que no se pueda hacer fuerza bruta
    sobre el espacio de ids.
    """
    material = f"{settings.SECRET_KEY}:{business.pk}".encode()
    return hashlib.sha256(material).hexdigest()[:16]


from analytics.aggregates import daily_summary

from .models import CorpusEntry


def extraer_entrada(business, day):
    """Convierte el día de un negocio en una entrada anónima del corpus.

    Devuelve None si el negocio optó por no compartir o si no hubo actividad.
    """
    if not business.comparte_corpus:
        return None

    resumen = daily_summary(business, day)
    if resumen["total_visitors"] == 0 and not resumen["hourly"]:
        return None

    entrada, _ = CorpusEntry.objects.update_or_create(
        huella=hash_negocio(business),
        day=day,
        defaults={
            "cohorte": business.kind,
            "visitantes": resumen["total_visitors"],
            "aforo_pico": resumen["peak_occupancy"],
            "espera_fila_seg": resumen["avg_queue_seconds"],
            "cobertura_personal": resumen["staff_coverage_pct"],
            "hora_pico": resumen["peak_hour"],
        },
    )
    return entrada


import statistics
from datetime import timedelta

METRICAS = [
    ("visitantes", "visitantes"),
    ("aforo_pico", "aforo_pico"),
    ("espera_fila_seg", "espera_fila_seg"),
    ("cobertura_personal", "cobertura_personal"),
]


def comparativa(business, day, ventana_dias=30):
    """Compara un negocio contra su cohorte. None si la cohorte es muy chica.

    Devuelve mediana (no promedio: un atípico arruina el promedio) y percentil.
    """
    propia = hash_negocio(business)
    desde = day - timedelta(days=ventana_dias)

    pares = CorpusEntry.objects.filter(
        cohorte=business.kind, day__gte=desde, day__lte=day
    ).exclude(huella=propia)

    if pares.values("huella").distinct().count() < MIN_COHORTE:
        return None

    mias = CorpusEntry.objects.filter(huella=propia, day__gte=desde, day__lte=day)
    if not mias.exists():
        return None

    resultado = {"negocios_comparados": pares.values("huella").distinct().count(),
                 "ventana_dias": ventana_dias}

    for clave, campo in METRICAS:
        valores_pares = [v for v in pares.values_list(campo, flat=True) if v is not None]
        valores_propios = [v for v in mias.values_list(campo, flat=True) if v is not None]
        if not valores_pares or not valores_propios:
            continue

        propio = statistics.median(valores_propios)
        mediana = statistics.median(valores_pares)
        por_debajo = sum(1 for v in valores_pares if v < propio)
        resultado[clave] = {
            "propio": propio,
            "mediana_pares": mediana,
            "percentil": round(100 * por_debajo / len(valores_pares)),
        }

    return resultado
