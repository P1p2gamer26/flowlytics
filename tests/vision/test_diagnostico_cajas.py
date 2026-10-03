from vision.core.diagnostico_cajas import diagnosticar_pistas

def test_detecta_que_hace_falta_reescalar_si_frame_y_referencia_difieren():
    pistas = [{"t": 0.0, "cajas": [{"id": 1, "xyxy": [10, 10, 30, 90]}]}]

    resultado = diagnosticar_pistas(pistas, frame_wh=(100, 100), ref_wh=(200, 200))

    assert resultado["necesita_reescalar"] is True
    # Sin reescalar, una caja que llega hasta x=30 de 100 (30%) debería seguir
    # ocupando el 30% del ancho de referencia (60 de 200), no seguir en 30.
    assert resultado["cajas_fuera_de_referencia"] == 0

def test_misma_resolucion_no_hace_falta_reescalar():
    pistas = [{"t": 0.0, "cajas": [{"id": 1, "xyxy": [10, 10, 30, 90]}]}]

    resultado = diagnosticar_pistas(pistas, frame_wh=(100, 100), ref_wh=(100, 100))

    assert resultado["necesita_reescalar"] is False

def test_cuenta_cajas_que_quedarian_fuera_del_cuadro_de_referencia():
    # Una caja guardada sin escalar, más grande que la referencia: haría falta
    # detectar que se sale del cuadro si nadie la reescala.
    pistas = [{"t": 0.0, "cajas": [{"id": 1, "xyxy": [150, 10, 250, 90]}]}]

    resultado = diagnosticar_pistas(pistas, frame_wh=(300, 300), ref_wh=(200, 200))

    assert resultado["cajas_fuera_de_referencia"] == 1

def test_el_salto_maximo_por_track_detecta_un_teletransporte():
    pistas = [
        {"t": 0.0, "cajas": [{"id": 1, "xyxy": [0, 0, 10, 10]}]},
        {"t": 0.5, "cajas": [{"id": 1, "xyxy": [5, 0, 15, 10]}]},
        {"t": 1.0, "cajas": [{"id": 1, "xyxy": [500, 0, 510, 10]}]},
    ]

    resultado = diagnosticar_pistas(pistas, frame_wh=(600, 600), ref_wh=(600, 600))

    assert resultado["salto_maximo_por_track"][1] > 400

def test_sin_pistas_no_revienta():
    resultado = diagnosticar_pistas([], frame_wh=(100, 100), ref_wh=(100, 100))
    assert resultado == {"necesita_reescalar": False,
                         "cajas_fuera_de_referencia": 0,
                         "salto_maximo_por_track": {}}
