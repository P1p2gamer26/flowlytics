"""Degradación honesta: si el worker no alcanza el FPS objetivo, muestrea menos
seguido en vez de acumular retraso, y marca la ventana como degradada.
"""


def ajustar_muestreo(fps_objetivo, fps_medido, tolerancia=0.8):
    if fps_medido < fps_objetivo * tolerancia:
        factor = int(fps_objetivo / max(fps_medido, 0.1))
        return max(factor, 1)
    return None
