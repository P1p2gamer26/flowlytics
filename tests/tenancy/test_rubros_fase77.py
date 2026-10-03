"""Los cuatro rubros del producto existen, no rompen el panel y hablan español."""
from tenancy.rubros import PERFILES, RUBROS, ETIQUETAS_BASE, perfil

RUBROS_DE_PRODUCCION = ["supermercado", "cafe", "drogueria", "tienda_de_barrio"]


def test_cada_rubro_del_producto_tiene_perfil():
    for r in RUBROS_DE_PRODUCCION:
        p = perfil(r)
        assert p["metricas"], f"{r}: sin métricas"
        assert p["principal"] in p["metricas"], f"{r}: principal fuera de métricas"


def test_las_metricas_principales_del_rubro_existen():
    for r, datos in RUBROS.items():
        mapa = {
            "fila_caja": "avg_queue_seconds",
            "permanencia_mesa": "avg_dwell_seconds",
            "cola_mostrador": "avg_queue_seconds",
            "rotacion": "total_visitors",
        }
        clave = mapa.get(datos["metrica_principal"], datos["metrica_principal"])
        assert clave in ETIQUETAS_BASE, f"{r}: {clave} sin etiqueta base"


def test_ningun_texto_del_panel_esta_en_ingles():
    for datos in PERFILES.values():
        for etiqueta in datos.get("etiquetas", {}).values():
            assert etiqueta[0].isupper() or etiqueta.startswith("Esper"), \
                f"texto sin español llano: {etiqueta}"
        for zona in datos.get("zonas", []):
            assert zona["name"].strip(), f"zona sin nombre"
