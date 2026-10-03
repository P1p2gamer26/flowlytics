import pytest

from vision.core.heatmap import (
    GridAccumulator, normalizar, rejilla_vacia, sumar_grids, suavizar,
)

def test_rejilla_vacia_tiene_filas_por_columnas():
    g = rejilla_vacia(cols=3, rows=2)
    assert g == [[0, 0, 0], [0, 0, 0]]

def test_el_acumulador_cuenta_una_pisada_por_celda():
    # cámara de referencia 80x40, celdas de 40 px -> rejilla 2x1
    acc = GridAccumulator(ref_wh=(80, 40), cell_px=40)
    assert (acc.cols, acc.rows) == (2, 1)
    acc.observe([(1, (10.0, 10.0)), (2, (70.0, 10.0)), (3, (10.0, 10.0))])
    grid, personas = acc.cerrar()
    assert grid == [[2, 1]]
    assert personas == 3

def test_cerrar_reinicia_el_acumulador():
    acc = GridAccumulator(ref_wh=(40, 40), cell_px=40)
    acc.observe([(1, (5.0, 5.0))])
    acc.cerrar()
    grid, personas = acc.cerrar()
    assert grid == [[0]]
    assert personas == 0

def test_una_pisada_fuera_del_frame_se_recorta_a_la_celda_del_borde():
    acc = GridAccumulator(ref_wh=(40, 40), cell_px=40)
    acc.observe([(1, (-5.0, 999.0))])
    grid, _ = acc.cerrar()
    assert grid == [[1]]

def test_sumar_grids_descarta_las_de_tamano_distinto():
    ventanas = [
        ([[1, 2]], 1, 2, 5),
        ([[10, 20]], 1, 2, 7),
        ([[1]], 1, 1, 100),  # tamaño distinto: se descarta
    ]
    grid, personas, descartadas = sumar_grids(ventanas)
    assert grid == [[11, 22]]
    assert personas == 12
    assert descartadas == 1

def test_sumar_grids_de_lista_vacia_no_revienta():
    assert sumar_grids([]) == ([], 0, 0)

def test_suavizar_promedia_con_los_vecinos():
    # rejilla 5x5 con el pico en el centro: la esquina queda a distancia
    # Chebyshev 2 del pico, fuera de su ventana de vecinos inmediatos (en una
    # rejilla 3x3 la esquina siempre es vecina diagonal del centro y no se
    # puede aislar del pico).
    grid = [[0] * 5 for _ in range(5)]
    grid[2][2] = 9
    suave = suavizar(grid)
    # la celda central tiene 8 vecinos + ella misma = 9 celdas, promedio 1.0
    assert suave[2][2] == pytest.approx(1.0)
    # una esquina tiene 3 vecinos + ella misma = 4 celdas, ninguna alcanza el pico
    assert suave[0][0] == pytest.approx(0.0)

def test_normalizar_deja_el_maximo_en_uno():
    assert normalizar([[0, 2], [4, 8]]) == [[0.0, 0.25], [0.5, 1.0]]

def test_normalizar_una_rejilla_vacia_no_revienta():
    assert normalizar([[0, 0], [0, 0]]) == [[0, 0], [0, 0]]
