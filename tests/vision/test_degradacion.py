from vision.core.degradacion import ajustar_muestreo


def test_si_alcanza_el_objetivo_no_degrada():
    salto = ajustar_muestreo(fps_objetivo=2.0, fps_medido=1.9)
    assert salto is None


def test_si_no_alcanza_el_objetivo_degrada_y_baja_el_muestreo():
    salto = ajustar_muestreo(fps_objetivo=2.0, fps_medido=0.8)
    assert salto is not None and salto > 1


def test_fps_medido_cero_no_divide_por_cero():
    salto = ajustar_muestreo(fps_objetivo=2.0, fps_medido=0.0)
    assert salto is not None and salto > 1
