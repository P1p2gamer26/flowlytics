import numpy as np
import supervision as sv

from vision.anotar import guardar_muestras, pintar_detecciones
from vision.anotar import Permanencias, etiqueta


def _dets(cajas):
    return sv.Detections(
        xyxy=np.array(cajas, dtype=float),
        class_id=np.array([0] * len(cajas)),
        confidence=np.array([0.9] * len(cajas)),
        tracker_id=np.array(list(range(1, len(cajas) + 1))),
    )


def test_pinta_una_caja_por_persona_sin_tocar_el_frame_original():
    frame = np.zeros((120, 200, 3), dtype=np.uint8)
    salida = pintar_detecciones(frame, _dets([[10, 10, 50, 100], [90, 10, 130, 100]]))

    assert salida.shape == frame.shape
    assert frame.sum() == 0, "se pinto encima del frame original"
    assert salida.sum() > 0, "no se pinto nada"


def test_sin_detecciones_devuelve_el_frame_tal_cual():
    frame = np.full((60, 60, 3), 7, dtype=np.uint8)
    salida = pintar_detecciones(frame, sv.Detections.empty())
    assert np.array_equal(salida, frame)


def test_guarda_un_png_por_muestra(tmp_path):
    frame = np.zeros((60, 60, 3), dtype=np.uint8)
    rutas = guardar_muestras([(frame, _dets([[5, 5, 20, 50]]))] * 3, tmp_path)

    assert len(rutas) == 3
    assert all(r.exists() and r.suffix == ".png" for r in rutas)
    assert len({r.name for r in rutas}) == 3, "se pisaron entre ellas"


def test_cuenta_desde_que_vio_a_la_persona_por_primera_vez():
    p = Permanencias()
    p.ver([7], 100.0)
    p.ver([7], 160.0)
    assert p.segundos(7) == 60.0


def test_cada_persona_lleva_su_propio_reloj():
    p = Permanencias()
    p.ver([1], 0.0)
    p.ver([1, 2], 30.0)
    assert p.segundos(1) == 30.0
    assert p.segundos(2) == 0.0


def test_a_quien_no_ha_visto_no_le_inventa_tiempo():
    assert Permanencias().segundos(99) == 0.0


def test_la_etiqueta_se_lee_como_en_la_referencia():
    assert etiqueta(3, 125.0, es_personal=False) == "2 min"
    assert etiqueta(3, 4530.0, es_personal=False) == "1 h 15 min"
    assert etiqueta(3, 30.0, es_personal=False) == "menos de 1 min"
    # El personal no lleva reloj de permanencia: lleva ahi todo el turno.
    assert etiqueta(3, 4530.0, es_personal=True) == "personal"


def test_deteccion_baja_confianza_no_se_pinta_como_persona_confiable():
    """Cuando la confianza es muy baja la caja no se distingue de fondo y no
    genera una etiqueta de persona: no se le hace creer al dueño que eso es
    alguien real."""
    frame = np.full((100, 200, 3), 200, dtype=np.uint8)
    dets = sv.Detections(
        xyxy=np.array([[10, 10, 50, 90]], dtype=float),
        class_id=np.array([0]),
        confidence=np.array([0.10]),
        tracker_id=np.array([None]),
    )
    salida = pintar_detecciones(frame, dets)

    assert np.array_equal(salida, frame), "una deteccion a 10% no deberia pintar caja"


def test_deteccion_de_confianza_umbral_sigue_pintando():
    """La confianza en el umbral es la frontera: si pasa, se pinta."""
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    dets = sv.Detections(
        xyxy=np.array([[10, 10, 50, 90]], dtype=float),
        class_id=np.array([0]),
        confidence=np.array([0.25]),
        tracker_id=np.array([None]),
    )
    salida = pintar_detecciones(frame, dets)
    assert salida.sum() > 0, "al umbral hay que pintarlo"


def test_la_caja_es_suficientemente_gruesa_para_verse_en_el_editor():
    """thickness=1 apenas se nota en el preview del editor. La caja pintada
    debe cubrir al menos 4 px en el borde del bbox (2 por lado)."""
    frame = np.full((100, 200, 3), 255, dtype=np.uint8)
    dets = sv.Detections(
        xyxy=np.array([[10, 10, 50, 90]], dtype=float),
        class_id=np.array([0]),
        confidence=np.array([0.9]),
        tracker_id=np.array([1]),
    )
    salida = pintar_detecciones(frame, dets)

    borde_arriba = salida[9:11, 10:50, 0]
    borde_abajo = salida[89:91, 10:50, 0]
    borde_izq = salida[10:90, 9:11, 0]
    borde_der = salida[10:90, 49:51, 0]
    pintados = [borde_arriba, borde_abajo, borde_izq, borde_der]
    assert all(b.min() < 255 for b in pintados), \
        "la caja no se nota en ningun borde del bbox"
