import numpy as np

from vision.personal_demo import cargar_regiones, clasificar, es_trabajador, pintar_roles

MOSTRADOR = [np.array([[0.0, 0.0], [0.5, 0.0], [0.5, 0.5], [0.0, 0.5]])]
FRAME = (100, 100)


def test_pie_dentro_es_trabajador_y_fuera_cliente():
    assert es_trabajador([10, 10, 30, 40], MOSTRADOR, FRAME)      # pie (20, 40)
    assert not es_trabajador([60, 60, 80, 90], MOSTRADOR, FRAME)  # pie (70, 90)
    assert clasificar([[10, 10, 30, 40], [60, 60, 80, 90]], MOSTRADOR, FRAME) == [True, False]


def test_sin_regiones_todos_son_clientes():
    assert clasificar([[10, 10, 30, 40]], [], FRAME) == [False]


def test_regiones_demo_por_nombre_de_video_en_0_1():
    regs = cargar_regiones("demo/videos/cctv/super_caja.mp4", ref_wh=(1920, 1080))
    assert len(regs) == 2
    assert all(r.min() >= 0 and r.max() <= 1 for r in regs)
    assert cargar_regiones("otro.mp4") == []


def test_pintar_roles_colorea_la_caja():
    frame = np.zeros((100, 100, 3), np.uint8)
    out = pintar_roles(frame, [[20, 40, 60, 90]], [True])
    assert out.shape == frame.shape and not frame.any()
    assert tuple(out[65, 20]) == (201, 99, 37)  # borde izquierdo de la caja, azul
