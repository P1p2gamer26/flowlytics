"""Qué mide cada rubro, cómo se llama y qué zonas se dibujan.

Esto es una tabla de datos, no lógica. Cambiar la métrica principal de un rubro
es editar una línea de aquí: no se toca el panel, ni el editor de zonas, ni el
prompt del LLM.

Dos reglas al editar:

- Las claves de `metricas` son claves de `analytics.aggregates.daily_summary`.
  Una que no exista sale como un guion en el panel; `tests/tenancy/test_rubros.py`
  no deja que pase.
- Los `kind` de `zonas` son de `cameras.models.CONTEXTOS`, porque de eso dependen
  las reglas de evento del pipeline.
- Las claves de `avisos` son tipos de `vision.core.events.CATALOGO`, y el
  número está en la unidad que ese catálogo declara: segundos para una
  espera, personas para un aforo. Un tipo que no se lista, no se avisa.

Sin imports de Django a propósito: lo leen `analytics`, `cameras`, `insights` y
`tenancy`, y un módulo de datos puro no crea ciclos con ninguno.
"""

# Nombre por defecto de cada cifra. Un rubro solo escribe las que llama distinto.
ETIQUETAS_BASE = {
    "total_visitors": "Visitantes del día",
    "entradas": "Entradas",
    "salidas": "Salidas",
    "peak_occupancy": "Aforo máximo",
    "peak_hour": "Hora pico",
    "avg_queue_seconds": "Espera en fila",
    "avg_dwell_seconds": "Permanencia media",
    "staff_coverage_pct": "Cobertura de personal",
}

# La primera métrica de la lista es la principal del rubro y sale primera en el
# panel. Ese orden es la propuesta del plan; confirmarlo es de Julián.
PERFILES = {
    "cafe": {
        "metricas": ["avg_dwell_seconds", "total_visitors", "peak_hour",
                     "avg_queue_seconds", "staff_coverage_pct"],
        "etiquetas": {
            "avg_dwell_seconds": "Permanencia en mesa",
            "avg_queue_seconds": "Espera para pedir",
            "total_visitors": "Clientes del día",
            "staff_coverage_pct": "Barra atendida",
        },
        "zonas": [
            {"name": "Mesas", "kind": "general"},
            {"name": "Barra", "kind": "counter"},
            {"name": "Fila para pedir", "kind": "queue"},
            {"name": "Entrada", "kind": "entrada"},
        ],
        "foco": "En un café lo que decide el negocio es cuánto se queda la gente en la "
                "mesa y cuánta rota: una permanencia muy corta es consumo apurado y una "
                "muy larga es una mesa que no factura. Una fila larga para pedir cuesta "
                "clientes que se van antes de ordenar.",
        "avisos": {"long_queue": 240.0, "crowded_queue": 4.0,
                   "empty_counter": 1.0, "overcrowding": 25.0},
    },
    "restaurant": {
        "metricas": ["avg_dwell_seconds", "total_visitors", "peak_hour",
                     "avg_queue_seconds", "staff_coverage_pct"],
        "etiquetas": {
            "avg_dwell_seconds": "Permanencia en mesa",
            "avg_queue_seconds": "Espera para mesa",
            "total_visitors": "Comensales del día",
            "staff_coverage_pct": "Salón atendido",
        },
        "zonas": [
            {"name": "Salón", "kind": "general"},
            {"name": "Espera para mesa", "kind": "queue"},
            {"name": "Caja", "kind": "counter"},
            {"name": "Entrada", "kind": "entrada"},
        ],
        "foco": "En un restaurante la mesa es el recurso escaso: la permanencia dice "
                "cuántos turnos entran en un servicio, y la espera para mesa en la hora "
                "pico dice cuánta gente se está yendo antes de sentarse.",
        "avisos": {"long_queue": 600.0, "crowded_queue": 6.0,
                   "empty_counter": 1.0, "overcrowding": 40.0},
    },
    "retail": {
        "metricas": ["avg_queue_seconds", "total_visitors", "peak_hour",
                     "peak_occupancy", "staff_coverage_pct"],
        "etiquetas": {
            "avg_queue_seconds": "Cola en caja",
            "total_visitors": "Compradores del día",
            "staff_coverage_pct": "Cajas atendidas",
        },
        "zonas": [
            {"name": "Cajas", "kind": "counter"},
            {"name": "Fila de caja", "kind": "queue"},
            {"name": "Pasillo principal", "kind": "pasillo"},
            {"name": "Entrada", "kind": "entrada"},
        ],
        "foco": "En una tienda o supermercado la cola en caja es lo que hace abandonar "
                "un carrito lleno; cruzada con la hora pico dice a qué hora falta una "
                "caja abierta. El aforo por pasillo dice qué zona del local trabaja.",
        "avisos": {"long_queue": 300.0, "crowded_queue": 5.0,
                   "empty_counter": 1.0, "overcrowding": 40.0},
    },
    "classroom": {
        "metricas": ["peak_occupancy", "total_visitors", "peak_hour",
                     "avg_dwell_seconds"],
        "etiquetas": {
            "peak_occupancy": "Asistencia máxima",
            "total_visitors": "Personas distintas",
            "avg_dwell_seconds": "Permanencia media",
        },
        "zonas": [
            {"name": "Aula", "kind": "general"},
            {"name": "Entrada", "kind": "entrada"},
        ],
        "foco": "En un aula lo que importa es cuánta gente hubo y cuánto se quedó: no "
                "hay fila ni mostrador, y medir 'cobertura de personal' no significa "
                "nada. La asistencia máxima y la permanencia describen el uso del salón.",
        # Ni fila ni mostrador: en un aula solo tiene sentido el aforo.
        "avisos": {"overcrowding": 35.0},
    },
    "other": {
        "metricas": ["total_visitors", "peak_occupancy", "peak_hour",
                     "avg_dwell_seconds", "staff_coverage_pct"],
        "etiquetas": {},
        "zonas": [
            {"name": "Zona principal", "kind": "general"},
            {"name": "Entrada", "kind": "entrada"},
        ],
        "foco": "Sin un rubro definido, lo que aplica a cualquier local: cuánta gente "
                "entró, a qué hora se llenó y cuánto se quedó.",
        "avisos": {"long_queue": 300.0, "overcrowding": 40.0},
    },
    "supermercado": {
        "metricas": ["avg_queue_seconds", "total_visitors", "peak_hour",
                      "peak_occupancy", "staff_coverage_pct"],
        "etiquetas": {
            "avg_queue_seconds": "Fila en caja",
            "avg_dwell_seconds": "Permanencia media",
            "total_visitors": "Compradores del día",
            "staff_coverage_pct": "Cajas atendidas",
        },
        "zonas": [
            {"name": "Cajas", "kind": "counter"},
            {"name": "Fila de caja", "kind": "queue"},
            {"name": "Pasillo principal", "kind": "pasillo"},
            {"name": "Entrada", "kind": "entrada"},
        ],
        "foco": "En un supermercado la fila en caja es lo que hace abandonar un carrito; "
                "la cobertura de cajas y la hora pico dicen cuándo falta abrir otra.",
        "avisos": {"long_queue": 300.0, "crowded_queue": 5.0,
                   "empty_counter": 1.0, "overcrowding": 40.0},
    },
    "drogueria": {
        "metricas": ["avg_queue_seconds", "total_visitors", "peak_hour",
                      "peak_occupancy", "staff_coverage_pct"],
        "etiquetas": {
            "avg_queue_seconds": "Cola en mostrador",
            "avg_dwell_seconds": "Permanencia media",
            "total_visitors": "Clientes del día",
            "staff_coverage_pct": "Mostrador atendido",
        },
        "zonas": [
            {"name": "Mostrador", "kind": "counter"},
            {"name": "Cola de mostrador", "kind": "queue"},
            {"name": "Entrada", "kind": "entrada"},
        ],
        "foco": "En una droguería la cola en el mostrador es lo que retrasa la entrega; "
                "el aforo dice cuánto espacio hay antes de que se forme fila.",
        "avisos": {"long_queue": 180.0, "crowded_queue": 4.0,
                   "empty_counter": 1.0, "overcrowding": 25.0},
    },
    "tienda_de_barrio": {
        "metricas": ["total_visitors", "avg_dwell_seconds", "peak_hour",
                      "avg_queue_seconds", "peak_occupancy"],
        "etiquetas": {
            "total_visitors": "Rotación del día",
            "avg_dwell_seconds": "Tiempo por cliente",
            "avg_queue_seconds": "Espera en caja",
        },
        "zonas": [
            {"name": "Cajas", "kind": "counter"},
            {"name": "Fila", "kind": "queue"},
            {"name": "Entrada", "kind": "entrada"},
        ],
        "foco": "En una tienda de barrio la rotación (cuánta gente entra y sale) "
                "y el tiempo por cliente dicen si la tienda vende o solo recibe.",
        "avisos": {"long_queue": 60.0, "crowded_queue": 3.0,
                   "empty_counter": 1.0, "overcrowding": 30.0},
    },
}


RUBROS = {
    "supermercado": {
        "metrica_principal": "fila_caja",
        "umbral_default": 300,
    },
    "cafe": {
        "metrica_principal": "permanencia_mesa",
        "umbral_default": 120,
    },
    "drogueria": {
        "metrica_principal": "cola_mostrador",
        "umbral_default": 180,
    },
    "tienda_barrio": {
        "metrica_principal": "rotacion",
        "umbral_default": 60,
    },
}


def perfil(kind):
    """Perfil listo para servir: métricas en orden, etiquetas ya resueltas, zonas
    sugeridas y el foco del rubro.

    Un `kind` desconocido cae en el perfil por defecto en vez de romper el panel:
    un negocio importado a mano o un tipo retirado del formulario no puede dejar
    a nadie sin cifras.
    """
    datos = PERFILES.get(kind, PERFILES["other"])
    metricas = datos["metricas"]
    return {
        "kind": kind,
        "principal": metricas[0],
        "metricas": metricas,
        "etiquetas": {m: datos["etiquetas"].get(m, ETIQUETAS_BASE[m]) for m in metricas},
        "zonas": datos["zonas"],
        "avisos": datos["avisos"],
        "foco": datos["foco"],
    }
