from vision.core.rastros import rastros_de_pistas

def test_agrupa_las_cajas_por_track_id_y_conserva_el_tiempo():
    rastros = rastros_de_pistas([
        {"t": 0.0, "cajas": [{"id": 2, "xyxy": [0, 10, 20, 50]},
                              {"id": 1, "xyxy": [30, 10, 50, 70]}]},
        {"t": 0.5, "cajas": [{"id": 2, "xyxy": [10, 20, 30, 80]}]},
    ])

    assert rastros == [
        {"track_id": 2, "puntos": [{"t": 0.0, "xy": [10.0, 50.0]},
                                    {"t": 0.5, "xy": [20.0, 80.0]}]},
        {"track_id": 1, "puntos": [{"t": 0.0, "xy": [40.0, 70.0]}]},
    ]

def test_un_instante_sin_cajas_y_un_recorrido_vacio_no_inventan_rastros():
    assert rastros_de_pistas([{"t": 0.0, "cajas": []}]) == []
    assert rastros_de_pistas([]) == []
