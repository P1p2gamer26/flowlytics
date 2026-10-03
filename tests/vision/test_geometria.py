from vision.core.geometria import pie_de_caja

def test_el_pie_es_el_centro_del_borde_inferior():
    assert pie_de_caja([10, 20, 50, 120]) == (30.0, 120.0)

def test_una_caja_de_ancho_o_alto_cero_no_revienta():
    assert pie_de_caja([5, 5, 5, 5]) == (5.0, 5.0)
