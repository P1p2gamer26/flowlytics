"""Agrega muestras por-frame en ventanas de tiempo.

Sin Django, sin OpenCV: recibe números y devuelve números.
Los tracker_id se usan solo dentro de la ventana y se descartan al cerrarla:
nunca salen de este módulo.
"""
from dataclasses import dataclass, field


@dataclass
class WindowSummary:
    started_at: float
    ended_at: float
    samples: int
    occupancy_avg: dict[str, float]
    occupancy_max: dict[str, int]
    dwell_seconds: dict[str, float]
    unique_visitors: dict[str, int]
    crossings: dict[str, tuple[int, int]]


@dataclass
class _ZoneState:
    counts: list[int] = field(default_factory=list)
    first_seen: dict[int, float] = field(default_factory=dict)
    last_seen: dict[int, float] = field(default_factory=dict)


class MetricAccumulator:
    def __init__(self, window_seconds: int = 60):
        self._window = window_seconds
        self._start: float | None = None
        self._ultimo: float | None = None
        self._samples = 0
        self._zones: dict[str, _ZoneState] = {}
        self._crossings: dict[str, list[int]] = {}

    def observe(self, timestamp, zone_counts, tracker_ids_by_zone, line_deltas=None):
        if self._start is None:
            self._start = timestamp

        self._samples += 1
        self._ultimo = timestamp
        for name, count in zone_counts.items():
            state = self._zones.setdefault(name, _ZoneState())
            # una zona que aparece a mitad de ventana cuenta 0 en los muestreos previos
            missing = self._samples - 1 - len(state.counts)
            state.counts.extend([0] * missing)
            state.counts.append(count)

            for tid in tracker_ids_by_zone.get(name, ()):
                state.first_seen.setdefault(tid, timestamp)
                state.last_seen[tid] = timestamp

        for name, (entradas, salidas) in (line_deltas or {}).items():
            acc = self._crossings.setdefault(name, [0, 0])
            acc[0] += entradas
            acc[1] += salidas

        if timestamp - self._start < self._window:
            return None

        summary = self._build(timestamp)
        self._reset(timestamp)
        return summary

    def _build(self, ended_at):
        occupancy_avg, occupancy_max, dwell, unique = {}, {}, {}, {}
        for name, state in self._zones.items():
            counts = state.counts + [0] * (self._samples - len(state.counts))
            occupancy_avg[name] = sum(counts) / len(counts)
            occupancy_max[name] = max(counts)
            unique[name] = len(state.first_seen)
            if state.first_seen:
                spans = [state.last_seen[t] - state.first_seen[t] for t in state.first_seen]
                dwell[name] = sum(spans) / len(spans)
            else:
                dwell[name] = 0.0
        return WindowSummary(
            started_at=self._start,
            ended_at=ended_at,
            samples=self._samples,
            occupancy_avg=occupancy_avg,
            occupancy_max=occupancy_max,
            dwell_seconds=dwell,
            unique_visitors=unique,
            crossings={n: (e, s) for n, (e, s) in self._crossings.items()},
        )

    def cerrar(self):
        """Cierra la ventana en curso aunque no haya cumplido su duración.

        Un clip más corto que `window_seconds` no cerraba ninguna ventana y todo
        lo medido se perdía al terminar el archivo. Devuelve None si no hay nada
        que cerrar, para que llamarlo dos veces no invente una ventana vacía.
        """
        if self._start is None or self._samples == 0:
            return None
        summary = self._build(self._ultimo)
        self._reset(self._ultimo)
        return summary

    def _reset(self, timestamp):
        self._start = timestamp
        self._ultimo = None
        self._samples = 0
        self._zones = {}
        self._crossings = {}


@dataclass
class TrajectorySample:
    """El rastro de UN track dentro de una ventana de tiempo. Sirve para
    reconstruir la línea de izquierda a derecha en el visor.

    El orden de `points` es el orden en que se observaron los frames.
    """
    track_id: int
    started_at: float
    ended_at: float
    points: list[list[int]]


class TrajectoryAccumulator:
    """Acumula por (ventana, track_id) los puntos del centro del bbox.

    Vive en la misma ventana que `MetricAccumulator`. Cuando el acumulador de
    métricas cierra una ventana, este devuelve los `TrajectorySample` listos
    para persistir.

    Sin Django, sin OpenCV: recibe `[x, y]` y devuelve `[x, y]`. La
    persistencia es de quien llama.
    """

    def __init__(self, window_seconds: int = 60, max_points_per_track: int = 600):
        # Tope de puntos por track para no guardar trayectorias de alguien que
        # se quedó quieto toda la ventana: 600 puntos a 6 FPS = 100 s, más que
        # cualquier cliente. Una persona que no se mueve se queda en el primer
        # punto y se ignora el resto.
        self._window = window_seconds
        self._max_points = max_points_per_track
        self._start: float | None = None
        self._tracks: dict[int, list[list[int]]] = {}
        self._first_seen: dict[int, float] = {}
        self._last_seen: dict[int, float] = {}

    def observe(self, timestamp, track_centers):
        """`track_centers` es un dict `{track_id: [x, y]}` del frame actual.

        Solo se guardan los puntos que están dentro del frame. No son filtros
        rígidos a propósito: el detector ya recortó lo que no es una persona.
        """
        if self._start is None:
            self._start = timestamp

        for tid, center in track_centers.items():
            if center is None or len(center) < 2:
                continue
            x, y = int(center[0]), int(center[1])
            if x < 0 or y < 0:
                continue
            self._first_seen.setdefault(tid, timestamp)
            self._last_seen[tid] = timestamp
            points = self._tracks.setdefault(tid, [])
            if len(points) < self._max_points:
                points.append([x, y])

    def cerrar(self, ended_at: float) -> list[TrajectorySample]:
        """Cierra la ventana en curso y devuelve los trayectos persistibles.

        Un track que no se movió (todos los puntos iguales) no se devuelve: no
        se puede reconstruir un rastro sin desplazamiento.
        """
        if self._start is None or not self._tracks:
            self._reset(ended_at)
            return []

        samples = []
        for tid, points in self._tracks.items():
            if len(points) < 2:
                continue
            # Descartar quien se quedó quieto: todos los puntos iguales.
            if all(p == points[0] for p in points):
                continue
            samples.append(TrajectorySample(
                track_id=tid,
                started_at=self._first_seen[tid],
                ended_at=self._last_seen[tid],
                points=points,
            ))
        self._reset(ended_at)
        return samples

    def _reset(self, timestamp):
        self._start = timestamp
        self._tracks = {}
        self._first_seen = {}
        self._last_seen = {}
