from vision.core.events import DEFAULT_RULES, EventRule, detect_events
from vision.core.metrics import WindowSummary


def summary(**overrides):
    base = dict(
        started_at=0.0, ended_at=60.0, samples=120,
        occupancy_avg={}, occupancy_max={}, dwell_seconds={}, unique_visitors={},
        crossings={},
    )
    base.update(overrides)
    return WindowSummary(**base)


ZONE_KINDS = {"fila": "queue", "barra": "staff", "salon": "general"}


def test_long_queue_fires_above_threshold():
    s = summary(occupancy_avg={"fila": 4.0}, occupancy_max={"fila": 6},
                dwell_seconds={"fila": 240.0}, unique_visitors={"fila": 10})

    events = detect_events(s, ZONE_KINDS, DEFAULT_RULES)

    assert [e["kind"] for e in events] == ["long_queue"]
    assert events[0]["zone_name"] == "fila"
    assert events[0]["value"] == 240.0


def test_long_queue_silent_below_threshold():
    s = summary(occupancy_avg={"fila": 1.0}, occupancy_max={"fila": 2},
                dwell_seconds={"fila": 60.0}, unique_visitors={"fila": 5})

    assert detect_events(s, ZONE_KINDS, DEFAULT_RULES) == []


def test_empty_counter_fires_when_staff_zone_had_nobody():
    s = summary(occupancy_avg={"barra": 0.0}, occupancy_max={"barra": 0},
                dwell_seconds={"barra": 0.0}, unique_visitors={"barra": 0})

    events = detect_events(s, ZONE_KINDS, DEFAULT_RULES)

    assert [e["kind"] for e in events] == ["empty_counter"]


def test_rules_only_apply_to_their_zone_kind():
    # 'salon' es general: la regla de fila no debe mirarlo aunque el dwell sea alto
    s = summary(occupancy_avg={"salon": 2.0}, occupancy_max={"salon": 3},
                dwell_seconds={"salon": 900.0}, unique_visitors={"salon": 4})

    assert detect_events(s, ZONE_KINDS, DEFAULT_RULES) == []


def test_custom_rule_on_occupancy_max():
    rule = EventRule(kind="overcrowding", zone_kind="general",
                     field="occupancy_max", threshold=10)
    s = summary(occupancy_avg={"salon": 8.0}, occupancy_max={"salon": 15},
                dwell_seconds={"salon": 100.0}, unique_visitors={"salon": 20})

    events = detect_events(s, ZONE_KINDS, [rule])

    assert events == [{"kind": "overcrowding", "zone_name": "salon", "value": 15}]
