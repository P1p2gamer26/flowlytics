"""Estelas vivas: últimas posiciones de cada track en tiempo real.

Puro Python, sin Django. El worker la alimenta cuadro a cuadro y la vista
la lee desde un JSON atómico cada ~0.5 s. No toca la BD; Trajectory
sigue guardándose igual al cerrar cada ventana.
"""
from collections import deque
import time


class EstelasVivas:
    """Mantiene los últimos puntos de cada track_id visto recientemente.

    Args:
        max_puntos: Máximo de puntos por track (deque maxlen).
        max_edad_s: Segundos tras los que un track se considera viejo y se purga.
    """

    def __init__(self, max_puntos: int = 6, max_edad_s: float = 3.0):
        self.max_puntos = max_puntos
        self.max_edad_s = max_edad_s
        self._tracks: dict[int, deque[tuple[int, int]]] = {}
        self._ultimo_t: dict[int, float] = {}

    def observar(self, pies: list[tuple[int, tuple[float, float]]], t: float) -> None:
        """Añade un punto a cada track_id y actualiza su último timestamp.

        Args:
            pies: Lista de (track_id, (x, y)) en coordenadas de referencia.
            t: Timestamp monotónico del cuadro actual (time.monotonic()).
        """
        for track_id, (x, y) in pies:
            if track_id not in self._tracks:
                self._tracks[track_id] = deque(maxlen=self.max_puntos)
            self._tracks[track_id].append((int(round(x)), int(round(y))))
            self._ultimo_t[track_id] = t

    def recientes(self, t: float) -> list[dict]:
        """Devuelve tracks vistos hace <= max_edad_s y con >= 2 puntos.

        Args:
            t: Timestamp monotónico actual (time.monotonic()).

        Returns:
            Lista de dicts: {'track_id': int, 'points': [[x, y], ...]}.
            Purga tracks viejos internamente.
        """
        corte = t - self.max_edad_s
        vivos = []
        for track_id, puntos_deque in list(self._tracks.items()):
            ut = self._ultimo_t.get(track_id, 0)
            if ut < corte:
                self._tracks.pop(track_id, None)
                self._ultimo_t.pop(track_id, None)
                continue
            puntos = list(puntos_deque)
            if len(puntos) >= 2:
                vivos.append({"track_id": track_id, "points": puntos})
        return vivos