"""Une detección, tracking, zonas y métricas.

No sabe de dónde vienen los frames ni a dónde van los resultados: eso es de run_camera.
"""
from dataclasses import dataclass

from django.conf import settings
import supervision as sv

from vision.core.deadzone import aplicar_zona_muerta
from vision.core.events import detect_events
from vision.core.metrics import TrajectoryAccumulator, WindowSummary
from vision.core.tracking import crear_tracker


@dataclass
class PipelineResult:
    summary: WindowSummary | None
    events: list[dict]
    detections: sv.Detections
    trajectories: list  # list[TrajectorySample] ready to persist; empty if no window closed


def _track_centers(detections: sv.Detections) -> dict[int, list]:
    """Centro del bbox por cada track confirmado, en píxeles del frame actual."""
    result = {}
    if detections.tracker_id is None:
        return result
    for i in range(len(detections)):
        tid = detections.tracker_id[i]
        if tid is None:
            continue
        xyxy = detections.xyxy[i]
        cx = int((xyxy[0] + xyxy[2]) / 2)
        cy = int((xyxy[1] + xyxy[3]) / 2)
        result[int(tid)] = [cx, cy]
    return result


class Pipeline:
    def __init__(self, detector, zone_set, zone_kinds, accumulator, rules,
                 tracker=None, line_set=None, zona_muerta=None,
                 trajectory_acc=None):
        self._detector = detector
        self._zones = zone_set
        self._zone_kinds = zone_kinds
        self._accumulator = accumulator
        self._rules = rules
        # Sin tracker explicito se usa la fabrica calibrada, no `sv.ByteTrack()`
        # crudo: ese asume 30 FPS y confirma tracks de un solo frame, que es
        # justo la configuracion que inflaba el conteo.
        self._tracker = tracker if tracker is not None else crear_tracker(settings.SAMPLE_FPS)
        self._lines = line_set
        self._zona_muerta = zona_muerta
        self._traj_acc = trajectory_acc

    def process(self, frame, timestamp) -> PipelineResult:
        raw_detections = aplicar_zona_muerta(self._detector.detect(frame), self._zona_muerta)
        tracked_detections = self._tracker.update_with_detections(raw_detections)

        # ByteTrack no confirma un track nuevo hasta el frame siguiente a su
        # aparición, así que el aforo (que no necesita identidad) se cuenta
        # sobre las detecciones crudas; solo unique_visitors/dwell usan ids.
        counts, _ = self._zones.evaluate(raw_detections)
        _, ids_by_zone = self._zones.evaluate(tracked_detections)
        line_deltas = self._lines.update(tracked_detections) if self._lines else None

        if self._traj_acc is not None:
            self._traj_acc.observe(timestamp, _track_centers(tracked_detections))

        summary = self._accumulator.observe(timestamp, counts, ids_by_zone, line_deltas)
        if summary is None:
            return PipelineResult(summary=None, events=[], detections=tracked_detections, trajectories=[])

        # Cuando la ventana de métricas se cierra, también cerramos la de
        # trayectorias y devolvemos sus muestras para que la capa de
        # persistencia las guarde. Después se reinicia sola.
        trajectories = self._traj_acc.cerrar(
            summary.ended_at) if self._traj_acc is not None else []
        events = detect_events(summary, self._zone_kinds, self._rules)
        return PipelineResult(summary=summary, events=events, detections=tracked_detections,
                              trajectories=trajectories)

    def cerrar(self) -> PipelineResult:
        """Cierra la ventana en curso sin frame nuevo: el archivo se acabó.

        Las reglas de evento se evalúan igual que en `process`: una fila larga
        en los últimos 40 s del video es una fila larga.
        """
        summary = self._accumulator.cerrar()
        trajectories = self._traj_acc.cerrar(
            summary.ended_at) if self._traj_acc and summary else []
        if summary is None:
            return PipelineResult(summary=None, events=[], detections=sv.Detections.empty(), trajectories=[])
        return PipelineResult(summary=summary,
                              events=detect_events(summary, self._zone_kinds, self._rules),
                              detections=sv.Detections.empty(),
                              trajectories=trajectories)
