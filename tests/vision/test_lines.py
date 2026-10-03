import numpy as np
import supervision as sv

from vision.core.lines import LineSet


def _det(cx, cy, tid=1):
    """Una caja 20x40 centrada en (cx, cy); anchor BOTTOM_CENTER = (cx, cy+20)."""
    xyxy = np.array([[cx - 10, cy - 20, cx + 10, cy + 20]], dtype=float)
    return sv.Detections(xyxy=xyxy, tracker_id=np.array([tid]))


def _spec(name="puerta", puntos=((50, 100), (150, 100)), invertir=False):
    return {"name": name, "puntos": [list(puntos[0]), list(puntos[1])], "invertir": invertir}


def test_sin_cruce_no_cuenta_nada():
    ls = LineSet.from_specs([_spec()], frame_wh=(200, 200))
    ls.update(_det(100, 20))                  # anchor y=40, encima de la línea
    assert ls.update(_det(100, 10))["puerta"] == (0, 0)


def test_bajar_y_subir_deja_saldo_una_entrada_y_una_salida():
    ls = LineSet.from_specs([_spec()], frame_wh=(200, 200))
    ls.update(_det(100, 20))                  # anchor y=40 (arriba)
    e1, s1 = ls.update(_det(100, 140))["puerta"]   # anchor y=160 (abajo): cruza
    e2, s2 = ls.update(_det(100, 20))["puerta"]    # cruza de regreso
    assert (e1 + s1) == 1 and (e2 + s2) == 1       # un cruce cada vez
    assert (e1 + e2, s1 + s2) == (1, 1)            # neto: una entrada, una salida


def test_invertir_intercambia_entrada_y_salida():
    base = LineSet.from_specs([_spec(invertir=False)], frame_wh=(200, 200))
    inv = LineSet.from_specs([_spec(invertir=True)], frame_wh=(200, 200))
    for ls in (base, inv):
        ls.update(_det(100, 20))
    e_b, s_b = base.update(_det(100, 140))["puerta"]
    e_i, s_i = inv.update(_det(100, 140))["puerta"]
    assert (e_b, s_b) == (s_i, e_i)


def test_sin_tracker_id_no_cuenta():
    ls = LineSet.from_specs([_spec()], frame_wh=(200, 200))
    sin_id = sv.Detections(xyxy=np.array([[90, 80, 110, 120]], dtype=float))
    assert ls.update(sin_id)["puerta"] == (0, 0)


def test_escala_los_puntos_desde_la_referencia():
    # línea a y=100 en un frame de referencia 200x200, mostrada en 400x400 -> y=200
    ls = LineSet.from_specs([_spec()], frame_wh=(400, 400), ref_wh=(200, 200))
    ls.update(_det(200, 40))                  # anchor y=60 (arriba de y=200)
    e, s = ls.update(_det(200, 280))["puerta"]   # anchor y=300 (abajo): cruza
    assert (e + s) == 1


def test_convencion_de_sentido_la_salida_es_a_la_derecha_del_vector_ab():
    """Pin de la convención de sv.LineZone, no una preferencia nuestra.

    La línea va de A=(50,100) a B=(150,100): el vector A→B apunta a la derecha.
    Alguien que baja (de y=40 a y=160) la cruza pasando al lado DERECHO del
    vector (en coordenadas de pantalla y crece hacia abajo).
    sv.LineZone cuenta bajar como SALIDA (0, 1) y subir como ENTRADA (1, 0).
    Por tanto, la entrada es hacia el lado IZQUIERDO del vector A->B (hacia arriba, y disminuye).
    """
    ls = LineSet.from_specs([_spec()], frame_wh=(200, 200))
    ls.update(_det(100, 20))                      # anchor y=40: encima
    assert ls.update(_det(100, 140))["puerta"] == (0, 1)

