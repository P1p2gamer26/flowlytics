import time

class DobleRed:
    def __init__(self):
        self._cortada = False
        self._inicio_corte = 0

    def cortar(self):
        self._cortada = True
        self._inicio_corte = time.time()

    def restablecer(self):
        self._cortada = False
        self._inicio_corte = 0

    def cortada(self):
        return self._cortada

    def tiempo_corte(self):
        if not self._cortada:
            return 0
        return time.time() - self._inicio_corte
