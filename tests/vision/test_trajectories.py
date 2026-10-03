"""Tests del acumulador de trayectorias en el pipeline."""
import numpy as np
import supervision as sv

from vision.core.metrics import MetricAccumulator, TrajectoryAccumulator
from vision.pipeline import Pipeline


def dets(n):
    if n == 0:
        return sv.Detections.empty()
    xyxy = np.array([[10 + i * 5, 40, 14 + i * 5, 50] for i in range(n)], dtype=np.float32)
    return sv.Detections(
        xyxy=xyxy,
        class_id=np.zeros(n, dtype=int),
        confidence=np.full(n, 0.9, dtype=np.float32),
    )


def dets_with_ids(ids_and_xyxy):
    """Detections con tracker_id注入. Simula lo que ByteTrack devuelve."""
    n = len(ids_and_xyxy)
    xyxy = np.array([xy for _, xy in ids_and_xyxy], dtype=np.float32)
    track_id = np.array([tid for tid, _ in ids_and_xyxy], dtype=np.int64)
    return sv.Detections(
        xyxy=xyxy,
        class_id=np.zeros(n, dtype=int),
        confidence=np.full(n, 0.9, dtype=np.float32),
        tracker_id=track_id,
    )


ZONE_SPECS = [{"name": "sala", "kind": "general",
               "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]]}]
ZONE_KINDS = {"sala": "general"}


class FDS:
    """Fake detector que devuelve las detecciones pre-programadas por llamada."""
    def __init__(self, scripted):
        self._seq = list(scripted)

    def detect(self, frame):
        return self._seq.pop(0) if self._seq else dets(0)


class TrackedTracker:
    """Simula ByteTrack: devuelve las detecciones con tracker_id inyectados.
    El detector pasa detecciones sin ID; el tracker les pone IDs."""
    def __init__(self, ids_sequence):
        # Cada entrada es una lista de (track_id, [x1,y1,x2,y2])
        self._seq = list(ids_sequence)

    def update_with_detections(self, raw):
        if not self._seq:
            return dets(0)
        return dets_with_ids(self._seq.pop(0))


def build(window=60, trajectory=True):
    from vision.core.zones import ZoneSet
    traj_acc = TrajectoryAccumulator(window_seconds=window) if trajectory else None
    return Pipeline(
        detector=None,
        zone_set=ZoneSet.from_specs(ZONE_SPECS, frame_wh=(200, 200)),
        zone_kinds=ZONE_KINDS,
        accumulator=MetricAccumulator(window_seconds=window),
        rules=[],
        trajectory_acc=traj_acc,
    )


def test_devuelve_trayectorias_cuando_la_ventana_cierra():
    pipe = build(window=10)
    frame = np.zeros((200, 200, 3), dtype=np.uint8)

    # Track 1 avanza de x=10 a x=15 en dos frames; track 2 quieto en x=30
    # (quedo quieto se filtra: no hay desplazamiento).
    pipe._tracker = TrackedTracker([[(1, [10, 40, 14, 50]), (2, [30, 40, 34, 50])],
                                    [(1, [15, 40, 19, 50]), (2, [30, 40, 34, 50])]])
    pipe._detector = FDS([dets(1), dets(1)])

    pipe.process(frame, timestamp=0.0)
    result = pipe.process(frame, timestamp=10.0)

    assert result.summary is not None
    # Track 1 se movió → se devuelve; track 2 quedó quieto → se filtra.
    assert len(result.trajectories) == 1
    t1 = result.trajectories[0]
    assert t1.track_id == 1
    assert len(t1.points) == 2
    assert t1.points[0][0] < t1.points[1][0]  # izquierda -> derecha


def test_una_persona_quieta_no_devuelve_trayectoria():
    """Un solo punto tampoco forma rastro: se necesitan al menos 2."""
    pipe = build(window=10)
    frame = np.zeros((200, 200, 3), dtype=np.uint8)

    pipe._tracker = TrackedTracker([[(1, [10, 40, 14, 50])], [(1, [10, 40, 14, 50])]])
    pipe._detector = FDS([dets(1), dets(1)])

    pipe.process(frame, timestamp=0.0)
    result = pipe.process(frame, timestamp=10.0)

    assert len(result.trajectories) == 0


def test_cerrar_devuelve_trayectorias_parciales():
    """cerrar() devuelve trayectorias aunque la ventana no se haya cumplido
    (archivo que termina antes de 60 s)."""
    pipe = build(window=60)
    frame = np.zeros((200, 200, 3), dtype=np.uint8)

    # 2 puntos antes de cerrar: el track se movió
    pipe._tracker = TrackedTracker([[(1, [10, 40, 14, 50])], [(1, [20, 40, 24, 50])]])
    pipe._detector = FDS([dets(1), dets(1)])

    pipe.process(frame, timestamp=0.0)
    pipe.process(frame, timestamp=1.0)
    final = pipe.cerrar()

    assert final.summary is not None
    assert len(final.trajectories) == 1


def test_track_centers_calcula_el_centro_del_bbox():
    from vision.pipeline import _track_centers
    dets_ = dets_with_ids([(1, [10, 20, 50, 80])])
    centers = _track_centers(dets_)
    assert centers[1] == [30, 50]  # (10+50)//2=30, (20+80)//2=50


def test_puntos_ordenados_permiten_reconstruir_izquierda_a_derecha():
    pipe = build(window=10)
    frame = np.zeros((200, 200, 3), dtype=np.uint8)

    # 5 puntos: izquierda -> derecha
    pipe._tracker = TrackedTracker([
        [(1, [10, 40, 14, 50])],
        [(1, [20, 40, 24, 50])],
        [(1, [30, 40, 34, 50])],
        [(1, [40, 40, 44, 50])],
        [(1, [50, 40, 54, 50])],
    ])
    pipe._detector = FDS([dets(1), dets(1), dets(1), dets(1), dets(1)])

    for t in [0.0, 2.0, 4.0, 6.0, 8.0]:
        pipe.process(frame, timestamp=t)
    result = pipe.process(frame, timestamp=10.0)

    t1 = next(t for t in result.trajectories if t.track_id == 1)
    xs = [p[0] for p in t1.points]
    assert xs == sorted(xs)  # ordenado por x
    assert xs[-1] > xs[0]    # progresión izquierda -> derecha
