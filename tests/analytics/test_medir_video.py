"""medir_video abre OpenCV y carga YOLO: no se ejercita aquí.

Lo que sí se vigila es que no vuelva a la forma que hacía imposible medir el
aforo — un ZoneSet vacío y una lectura del acumulador por la puerta de atrás.
Es un test de código fuente a propósito: el repo ya prueba así deploy.sh y
requirements.txt, y la alternativa es no probarlo.
"""
import inspect

from analytics.management.commands import reporte_precision as cmd_mod


def test_medir_video_evalua_una_zona_para_poder_reportar_aforo():
    fuente = inspect.getsource(cmd_mod.medir_video)
    assert "ZoneSet" in fuente, "sin zonas, occupancy_max sale vacío y aforo_max es 0"
    assert "_ZonasVacias" not in fuente
    assert not hasattr(cmd_mod, "_ZonasVacias"), "quedó el doble muerto en el módulo"


def test_medir_video_cierra_el_pipeline_por_la_via_publica():
    fuente = inspect.getsource(cmd_mod.medir_video)
    assert "_accumulator._build" not in fuente, "Pipeline.cerrar() existe justo para esto"
    assert "pipeline.cerrar()" in fuente
    assert "medir_desde_ventanas" in fuente
