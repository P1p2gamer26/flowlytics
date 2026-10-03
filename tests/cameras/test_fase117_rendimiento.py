from vision.core.degradacion import ajustar_muestreo


def test_cpu_saturada_salta_frames():
    r = ajustar_muestreo(1.0, 0.09)
    assert r is not None and r > 1  # salta frames en vez de acumular retraso


def test_fps_suficiente_no_salta():
    r = ajustar_muestreo(1.0, 1.2)
    assert not r or r <= 1