"""Construye el prompt del reporte diario a partir de métricas agregadas.

Solo texto y números agregados. Ni frames, ni tracker ids, ni datos de personas.
"""
import json

from tenancy.rubros import perfil

TEMPLATE = """Eres un consultor de operaciones para negocios físicos. Analiza \
las métricas de un día y da recomendaciones concretas y accionables.

Negocio: {name}
Tipo de establecimiento: {kind}
Qué importa en este rubro: {foco}
Fecha analizada: {date}

Métricas del día (medidas por visión artificial sobre las cámaras del local):
{metrics}

Guía de interpretación:
- occupancy_avg / occupancy_max: personas presentes en la zona.
- dwell_seconds: segundos promedio que una persona permanece en la zona. En una \
zona de tipo "queue" esto es el tiempo de espera.
- avg_dwell_seconds: permanencia media del cliente, promediada sobre las zonas que \
no son fila ni área de personal. avg_queue_seconds es lo mismo pero solo en las \
zonas de fila: uno es quedarse, el otro es esperar.
- staff_coverage_pct: porcentaje del tiempo en que hubo al menos una persona en la \
zona de personal.
- Las zonas de tipo "staff" miden cobertura del puesto, no productividad individual.

Responde en español con exactamente estas tres secciones:

## Qué está funcionando
Máximo 3 puntos, cada uno citando el número que lo respalda.

## Qué corregir
Máximo 3 puntos. Cada uno debe nombrar el número problemático y por qué importa \
para el negocio.

## Acciones para mañana
Máximo 3 acciones concretas, cada una asignable a una persona y verificable al \
día siguiente con estas mismas métricas.

Si algún dato falta o es insuficiente para concluir, dilo explícitamente en vez de \
inventar. No especules sobre personas individuales."""


BLOQUE_COMPARATIVO = """

Contexto comparativo (últimos {ventana} días, contra {n} negocios anónimos del
mismo tipo). Percentil = qué porcentaje de los pares queda por debajo de este
negocio en esa métrica:
{filas}

Usa esto para distinguir un problema real de una característica normal del
sector: un número que parece malo pero está en el percentil 80 de su cohorte no
es la prioridad. Nunca menciones ni especules sobre negocios concretos: los
datos comparativos son anónimos y agregados."""


def _filas_comparativas(comp):
    filas = []
    for clave, datos in comp.items():
        if not isinstance(datos, dict):
            continue
        filas.append(
            f"- {clave}: este negocio {datos['propio']}, "
            f"mediana de pares {datos['mediana_pares']}, "
            f"percentil {datos['percentil']}"
        )
    return "\n".join(filas)


def build_prompt(summary, business, comparativa=None):
    prompt = TEMPLATE.format(
        name=business.name,
        kind=business.get_kind_display(),
        foco=perfil(business.kind)["foco"],
        date=summary["date"],
        metrics=json.dumps(summary, indent=2, ensure_ascii=False),
    )
    if comparativa:
        prompt += BLOQUE_COMPARATIVO.format(
            ventana=comparativa["ventana_dias"],
            n=comparativa["negocios_comparados"],
            filas=_filas_comparativas(comparativa),
        )
    return prompt
