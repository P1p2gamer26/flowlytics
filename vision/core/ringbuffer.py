"""Buffer circular de frames en memoria, para volcar un clip cuando ocurre un evento.

Los frames viven aquí y en ningún otro lado: al desbordar el buffer se descartan.
"""
from collections import deque


class FrameRingBuffer:
    def __init__(self, seconds: int, fps: float):
        self.capacity = int(seconds * fps)
        self._frames = deque(maxlen=self.capacity)

    def push(self, frame):
        self._frames.append(frame)

    def frames(self):
        return list(self._frames)
