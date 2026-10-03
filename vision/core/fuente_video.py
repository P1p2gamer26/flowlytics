class FuenteVideo:
    def __init__(self, url):
        self.url = url
        self.activa = True
        self.luz = "normal"

    def cortar(self):
        self.activa = False

    def reconectar(self):
        self.activa = True

    def mala_luz(self):
        self.luz = "mala"

    def esta_activa(self):
        return self.activa

    def entregar_frames(self):
        if not self.activa:
            return []
        # En mala luz, devolver los mismos frames que en normal,
        # porque el detector debe ser el que decide la precisión.
        return [self._frame_base() for _ in range(5)]

    def _frame_base(self):
        # Un array simulado, no un archivo real
        import numpy as np
        return np.zeros((640, 480, 3), dtype="uint8")
