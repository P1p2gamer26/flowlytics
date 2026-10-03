"""El catálogo de avisos: qué se puede avisar y cómo se mide cada cosa.

Sin base de datos: `reglas_desde` es una función pura sobre dos dicts.
"""
from vision.core.events import CATALOGO, DEFAULT_RULES, EventRule, reglas_desde


def test_reglas_desde_umbrales_construye_una_regla_por_umbral():
    reglas = reglas_desde({"long_queue": 300.0, "overcrowding": 40.0})

    assert reglas == [
        EventRule("long_queue", "queue", "dwell_seconds", 300.0),
        EventRule("overcrowding", "general", "occupancy_max", 40.0),
    ]


def test_un_tipo_sin_umbral_no_genera_regla():
    # Así se apaga un aviso para un rubro que no lo necesita: no poniéndolo.
    assert reglas_desde({}) == []


def test_la_fila_con_mucha_gente_cuenta_personas_no_segundos():
    (regla,) = reglas_desde({"crowded_queue": 5})

    assert (regla.zone_kind, regla.field, regla.below) == ("queue", "occupancy_max", False)
    assert regla.threshold == 5.0


def test_la_caja_desatendida_dispara_por_debajo_del_umbral():
    (regla,) = reglas_desde({"empty_counter": 1})

    assert regla.below is True


def test_los_umbrales_cableados_de_siempre_no_cambian():
    # DEFAULT_RULES sigue existiendo y valiendo lo mismo: lo usan el humo y los
    # tests viejos del pipeline. Esta fase le quita el trono, no la vida.
    assert DEFAULT_RULES == [
        EventRule("long_queue", "queue", "dwell_seconds", 180.0),
        EventRule("empty_counter", "staff", "occupancy_max", 1.0, below=True),
        EventRule("overcrowding", "general", "occupancy_max", 40.0),
    ]


def test_cada_tipo_dice_en_qué_unidad_se_mide():
    # La unidad es lo que el panel necesita para preguntar "¿cuántos minutos?"
    # en vez de "¿cuántos dwell_seconds?".
    for kind, datos in CATALOGO.items():
        assert datos["unidad"] in ("segundos", "personas"), kind
        assert datos["field"] in ("occupancy_avg", "occupancy_max",
                                  "dwell_seconds", "unique_visitors"), kind
