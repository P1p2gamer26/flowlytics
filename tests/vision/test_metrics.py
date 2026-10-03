from vision.core.metrics import MetricAccumulator


def test_returns_none_before_window_closes():
    acc = MetricAccumulator(window_seconds=60)

    assert acc.observe(0.0, {"fila": 2}, {"fila": {1, 2}}) is None
    assert acc.observe(30.0, {"fila": 3}, {"fila": {1, 2, 3}}) is None


def test_emits_summary_when_window_closes():
    acc = MetricAccumulator(window_seconds=60)
    acc.observe(0.0, {"fila": 2}, {"fila": {1, 2}})
    acc.observe(30.0, {"fila": 4}, {"fila": {1, 2, 3, 4}})

    summary = acc.observe(60.0, {"fila": 3}, {"fila": {3, 4, 5}})

    assert summary is not None
    assert summary.started_at == 0.0
    assert summary.samples == 3
    assert summary.occupancy_avg["fila"] == 3.0   # (2+4+3)/3
    assert summary.occupancy_max["fila"] == 4


def test_counts_unique_visitors_across_the_window():
    acc = MetricAccumulator(window_seconds=60)
    acc.observe(0.0, {"fila": 2}, {"fila": {1, 2}})
    acc.observe(30.0, {"fila": 2}, {"fila": {2, 3}})
    summary = acc.observe(60.0, {"fila": 1}, {"fila": {3}})

    # ids vistos: 1,2,3 -> 3 visitantes distintos
    assert summary.unique_visitors["fila"] == 3


def test_dwell_is_average_seconds_per_visitor():
    acc = MetricAccumulator(window_seconds=60)
    # id 1 presente en los 3 muestreos (0s, 30s, 60s) -> 60s de permanencia
    # id 9 presente solo en el ultimo -> 0s
    acc.observe(0.0, {"fila": 1}, {"fila": {1}})
    acc.observe(30.0, {"fila": 1}, {"fila": {1}})
    summary = acc.observe(60.0, {"fila": 2}, {"fila": {1, 9}})

    assert summary.dwell_seconds["fila"] == 30.0   # (60 + 0) / 2


def test_window_resets_after_emitting():
    acc = MetricAccumulator(window_seconds=60)
    acc.observe(0.0, {"fila": 5}, {"fila": {1}})
    acc.observe(60.0, {"fila": 5}, {"fila": {1}})

    assert acc.observe(90.0, {"fila": 1}, {"fila": {7}}) is None
    summary = acc.observe(120.0, {"fila": 1}, {"fila": {7}})

    assert summary.occupancy_max["fila"] == 1   # la ventana anterior no contamina
    assert summary.started_at == 60.0


def test_handles_zone_appearing_midwindow():
    acc = MetricAccumulator(window_seconds=60)
    acc.observe(0.0, {"fila": 1}, {"fila": {1}})
    summary = acc.observe(60.0, {"fila": 1, "barra": 2}, {"fila": {1}, "barra": {4, 5}})

    assert summary.occupancy_max["barra"] == 2
    assert summary.occupancy_avg["barra"] == 1.0   # (0 + 2) / 2, ausente cuenta como 0


def test_cerrar_devuelve_lo_acumulado_aunque_no_se_cumpla_la_ventana():
    acc = MetricAccumulator(window_seconds=60)
    assert acc.observe(0.0, {"sala": 2}, {"sala": [1, 2]}) is None
    assert acc.observe(10.0, {"sala": 4}, {"sala": [1, 2, 3]}) is None

    summary = acc.cerrar()

    assert summary is not None
    assert summary.samples == 2
    assert summary.occupancy_max["sala"] == 4
    assert summary.unique_visitors["sala"] == 3
    assert summary.ended_at == 10.0


def test_cerrar_sin_muestras_no_inventa_una_ventana():
    assert MetricAccumulator(window_seconds=60).cerrar() is None


def test_cerrar_no_repite_la_ventana_dos_veces():
    acc = MetricAccumulator(window_seconds=60)
    acc.observe(0.0, {"sala": 1}, {})
    assert acc.cerrar() is not None
    assert acc.cerrar() is None
