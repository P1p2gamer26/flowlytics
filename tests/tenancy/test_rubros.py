"""La tabla de rubros: que exista para todos, que no mienta y que no explote.

Sin base de datos: `perfil` es una función pura sobre un dict.
"""
from cameras.models import CONTEXTOS
from tenancy.models import BUSINESS_KINDS
from tenancy.rubros import ETIQUETAS_BASE, PERFILES, perfil
from vision.core.events import CATALOGO

# Claves numéricas que `analytics.aggregates.daily_summary` devuelve y que el
# panel puede pintar como cifra. Si daily_summary cambia, este test lo dice.
MEDIBLES = {"total_visitors", "entradas", "salidas", "peak_occupancy", "peak_hour",
            "avg_queue_seconds", "avg_dwell_seconds", "staff_coverage_pct"}


def test_todos_los_tipos_de_negocio_tienen_perfil():
    for kind, _ in BUSINESS_KINDS:
        assert kind in PERFILES, f"{kind} no tiene perfil y el panel se queda mudo"


def test_las_metricas_de_cada_rubro_existen_en_el_resumen():
    for kind, datos in PERFILES.items():
        assert datos["metricas"], f"{kind} sin métricas: el panel quedaría vacío"
        for clave in datos["metricas"]:
            assert clave in MEDIBLES, f"{kind} pide {clave}, que nadie calcula"


def test_las_metricas_de_cada_rubro_no_se_repiten():
    for kind, datos in PERFILES.items():
        assert len(set(datos["metricas"])) == len(datos["metricas"]), \
            f"{kind} pinta dos veces la misma cifra"


def test_ninguna_metrica_se_queda_sin_nombre_en_castellano():
    for clave in MEDIBLES:
        assert clave in ETIQUETAS_BASE, f"{clave} saldría en el panel con su nombre en inglés"


def test_las_zonas_sugeridas_usan_tipos_que_el_pipeline_entiende():
    validos = {c for c, _ in CONTEXTOS}
    for kind, datos in PERFILES.items():
        assert datos["zonas"], f"{kind} no sugiere ninguna zona"
        for zona in datos["zonas"]:
            assert zona["kind"] in validos, f"{kind} sugiere el tipo {zona['kind']}, que no existe"
            assert zona["name"].strip()


def test_cada_rubro_dice_que_le_importa():
    # El foco va al prompt del LLM y al panel: vacío deja al modelo sin contexto
    # y al panel con una frase suelta.
    for kind, datos in PERFILES.items():
        assert len(datos["foco"]) > 20, f"{kind} sin foco escrito"


def test_el_perfil_de_un_cafe_pone_la_permanencia_primero():
    p = perfil("cafe")

    assert p["principal"] == "avg_dwell_seconds"
    assert p["metricas"][0] == "avg_dwell_seconds"
    assert p["etiquetas"]["avg_dwell_seconds"] == "Permanencia en mesa"


def test_el_perfil_de_una_tienda_pone_la_cola_de_caja_primero():
    p = perfil("retail")

    assert p["principal"] == "avg_queue_seconds"
    assert p["etiquetas"]["avg_queue_seconds"] == "Cola en caja"


def test_un_aula_no_muestra_cifras_que_no_le_dicen_nada():
    p = perfil("classroom")

    assert "avg_queue_seconds" not in p["metricas"]   # un aula no hace fila
    assert "staff_coverage_pct" not in p["metricas"]


def test_un_kind_que_nadie_registro_cae_en_el_perfil_por_defecto():
    # Un negocio viejo, un dato importado a mano, una opción retirada: el panel
    # tiene que seguir pintando.
    p = perfil("marciano")

    assert p["metricas"] == PERFILES["other"]["metricas"]
    assert p["kind"] == "marciano"


def test_el_perfil_trae_las_etiquetas_ya_resueltas():
    # El panel no tiene que saber que existe una tabla base: recibe el nombre
    # de cada cifra hecho.
    p = perfil("classroom")

    assert set(p["etiquetas"]) == set(p["metricas"])
    assert all(v for v in p["etiquetas"].values())


def test_cada_rubro_dice_cuándo_avisar():
    for kind, datos in PERFILES.items():
        assert datos["avisos"], f"{kind} no avisaría de nada"
        for tipo, umbral in datos["avisos"].items():
            assert tipo in CATALOGO, f"{kind} avisa de {tipo}, que nadie detecta"
            assert umbral > 0, f"{kind} pone un umbral de {umbral} en {tipo}"


def test_un_aula_no_avisa_de_filas_que_no_existen():
    # El rubro decide qué se vigila, no solo con qué número: en un aula no hay
    # fila ni mostrador, y un aviso de fila ahí es ruido garantizado.
    assert "long_queue" not in PERFILES["classroom"]["avisos"]
    assert "empty_counter" not in PERFILES["classroom"]["avisos"]


def test_la_espera_que_molesta_no_es_la_misma_en_un_café_que_en_un_restaurante():
    # Esperar 4 min por un café es mucho; esperar 4 min por una mesa, no.
    assert PERFILES["cafe"]["avisos"]["long_queue"] < \
           PERFILES["restaurant"]["avisos"]["long_queue"]


def test_el_perfil_servido_incluye_los_avisos():
    # El panel prellena el formulario con esto: si no sale de `perfil`, la
    # pantalla de avisos tendría que adivinar.
    assert perfil("retail")["avisos"]["long_queue"] == 300.0
    assert perfil("marciano-inexistente")["avisos"] == PERFILES["other"]["avisos"]
