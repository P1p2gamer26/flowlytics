import numpy as np
import supervision as sv

from vision.core.tracking import crear_tracker


def _det(cx):
    """Persona caminando; caja 40x80 centrada en (cx, 100)."""
    return sv.Detections(
        xyxy=np.array([[cx - 20, 60, cx + 20, 140]], dtype=float),
        class_id=np.array([0]), confidence=np.array([0.9]))


def _ids_de_una_pasada(fps, paso):
    """Recorre la MISMA trayectoria (de x=50 a x=350) con distinto muestreo.

    `paso` es cuánto avanza la persona entre frames vistos: a mayor fps, pasos
    mas cortos. La persona es una sola, asi que los ids distintos deben ser 1.
    """
    tracker = crear_tracker(fps=fps)
    vistos = set()
    for cx in range(50, 350, paso):
        salida = tracker.update_with_detections(_det(cx))
        if salida.tracker_id is not None:
            vistos.update(int(i) for i in salida.tracker_id)
    return vistos


def test_una_persona_es_una_persona_a_cualquier_muestreo():
    lentos = _ids_de_una_pasada(fps=2, paso=15)
    rapidos = _ids_de_una_pasada(fps=6, paso=5)
    assert len(lentos) == 1, f"a 2 FPS la partio en {len(lentos)} personas"
    assert len(rapidos) == 1, f"a 6 FPS la partio en {len(rapidos)} personas"


def test_una_deteccion_suelta_no_es_una_persona():
    """Un falso positivo de un solo frame no puede contar como visitante."""
    tracker = crear_tracker(fps=2)
    salida = tracker.update_with_detections(_det(200))
    ids = [] if salida.tracker_id is None else list(salida.tracker_id)
    assert ids == [], "una deteccion aislada se confirmo como persona"
