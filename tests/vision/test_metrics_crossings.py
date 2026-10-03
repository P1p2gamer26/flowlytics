from vision.core.metrics import MetricAccumulator


def test_acumula_entradas_y_salidas_por_linea_en_la_ventana():
    acc = MetricAccumulator(window_seconds=10)
    acc.observe(0, {}, {}, line_deltas={"puerta": (1, 0)})
    acc.observe(5, {}, {}, line_deltas={"puerta": (0, 1)})
    summary = acc.observe(10, {}, {}, line_deltas={"puerta": (2, 0)})

    assert summary is not None
    assert summary.crossings["puerta"] == (3, 1)


def test_sin_line_deltas_las_crossings_quedan_vacias():
    acc = MetricAccumulator(window_seconds=10)
    acc.observe(0, {"z": 1}, {})
    summary = acc.observe(10, {"z": 1}, {})
    assert summary.crossings == {}


def test_la_ventana_nueva_arranca_los_cruces_en_cero():
    acc = MetricAccumulator(window_seconds=10)
    acc.observe(0, {}, {}, line_deltas={"puerta": (2, 1)})
    acc.observe(10, {}, {}, line_deltas={"puerta": (0, 0)})   # cierra la 1a ventana
    s2 = acc.observe(20, {}, {}, line_deltas={"puerta": (1, 0)})
    assert s2.crossings["puerta"] == (1, 0)                    # no arrastra la anterior
