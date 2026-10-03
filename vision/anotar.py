from pathlib import Path

import cv2
import numpy as np
import supervision as sv

_COLOR_CLIENTE = sv.Color(r=0, g=200, b=0)    # verde
_COLOR_PERSONAL = sv.Color(r=0, g=0, b=200)   # azul

_UMBRAL_CONFIANZA = 0.25

_CAJAS = sv.BoxAnnotator(thickness=2)
_CAJAS_PERSONAL = sv.BoxAnnotator(color=_COLOR_PERSONAL, thickness=2)
_CAJAS_CLIENTE = sv.BoxAnnotator(color=_COLOR_CLIENTE, thickness=2)
_ETIQUETAS = sv.LabelAnnotator(text_scale=0.4, text_thickness=1)
_ETIQUETAS_PERSONAL = sv.LabelAnnotator(
    color=_COLOR_PERSONAL, text_scale=0.4, text_thickness=1
)
_ETIQUETAS_CLIENTE = sv.LabelAnnotator(
    color=_COLOR_CLIENTE, text_scale=0.4, text_thickness=1
)


def _tracker_ids_list(detecciones: sv.Detections):
    if detecciones.tracker_id is not None:
        return list(detecciones.tracker_id)
    return [None] * len(detecciones)


def pintar_detecciones(
    frame: np.ndarray,
    detecciones: sv.Detections,
    permanencias=None,
    ids_personal=(),
) -> np.ndarray:
    """Devuelve una COPIA con una caja por persona y su id de rastro.

    Si se pasa `permanencias` (instancia de Permanencias), la etiqueta muestra
    el tiempo en escena en vez de #id. Las cajas de personal van en azul; el
    resto en verde. Cuando no se usan permanencias ni ids_personal el
    comportamiento es idéntico al original (compatibilidad hacia atrás).
    """
    if len(detecciones) == 0:
        return frame
    confianza_ok = detecciones.confidence >= _UMBRAL_CONFIANZA
    detecciones = detecciones[confianza_ok]
    if len(detecciones) == 0:
        return frame
    lienzo = frame.copy()

    tids = _tracker_ids_list(detecciones)
    ids_personal_set = set(ids_personal)

    if not ids_personal_set:
        # Modo simple: un anotador, etiquetas basadas en id o permanencia
        lienzo = _CAJAS.annotate(lienzo, detecciones)
        etiquetas = _construir_etiquetas(tids, detecciones.confidence,
                                         permanencias, ids_personal_set)
        return _ETIQUETAS.annotate(lienzo, detecciones, labels=etiquetas)

    # Modo con personal: dos pasadas, una por grupo
    idx_personal = [i for i, tid in enumerate(tids)
                    if tid is not None and int(tid) in ids_personal_set]
    idx_cliente = [i for i in range(len(tids)) if i not in set(idx_personal)]

    if idx_personal:
        d_personal = detecciones[idx_personal]
        etqs_personal = _construir_etiquetas(
            [tids[i] for i in idx_personal],
            d_personal.confidence, permanencias, ids_personal_set,
        )
        lienzo = _CAJAS_PERSONAL.annotate(lienzo, d_personal)
        lienzo = _ETIQUETAS_PERSONAL.annotate(lienzo, d_personal,
                                               labels=etqs_personal)

    if idx_cliente:
        d_cliente = detecciones[idx_cliente]
        etqs_cliente = _construir_etiquetas(
            [tids[i] for i in idx_cliente],
            d_cliente.confidence, permanencias, ids_personal_set,
        )
        lienzo = _CAJAS_CLIENTE.annotate(lienzo, d_cliente)
        lienzo = _ETIQUETAS_CLIENTE.annotate(lienzo, d_cliente,
                                              labels=etqs_cliente)

    return lienzo


def _construir_etiquetas(tids, confianzas, permanencias, ids_personal_set):
    resultado = []
    for tid, conf in zip(tids, confianzas):
        if permanencias is not None and tid is not None:
            tid_int = int(tid)
            es_personal = tid_int in ids_personal_set
            segs = permanencias.segundos(tid_int)
            resultado.append(etiqueta(tid_int, segs, es_personal))
        elif tid is not None:
            resultado.append(f"#{tid}")
        else:
            resultado.append(f"{conf:.2f}")
    return resultado


def guardar_muestras(frames_y_detecciones, destino) -> list[Path]:
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    rutas = []
    for i, (frame, detecciones) in enumerate(frames_y_detecciones):
        ruta = destino / f"muestra_{i:03d}.png"
        cv2.imwrite(str(ruta), pintar_detecciones(frame, detecciones))
        rutas.append(ruta)
    return rutas


class Permanencias:
    """Cuanto lleva cada rastro en escena, desde que se le vio por primera vez.

    Es el mismo dato que `dwell_seconds`, con otro corte: aquel agrega por zona
    cada 60 s y este va por persona y en vivo, que es lo que se pinta encima de
    su caja en la referencia de docs/NORTE.md.
    """

    def __init__(self):
        self._primera_vez = {}
        self._ultima = {}

    def ver(self, track_ids, timestamp: float) -> None:
        for tid in track_ids:
            tid = int(tid)
            self._primera_vez.setdefault(tid, timestamp)
            self._ultima[tid] = timestamp

    def segundos(self, track_id: int) -> float:
        track_id = int(track_id)
        if track_id not in self._primera_vez:
            return 0.0
        return self._ultima[track_id] - self._primera_vez[track_id]


def etiqueta(track_id: int, segundos: float, es_personal: bool) -> str:
    if es_personal:
        return "personal"
    minutos = int(segundos // 60)
    if minutos < 1:
        return "menos de 1 min"
    if minutos < 60:
        return f"{minutos} min"
    return f"{minutos // 60} h {minutos % 60} min"
