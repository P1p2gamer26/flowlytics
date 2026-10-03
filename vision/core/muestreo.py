"""Qué frames de un video hay que analizar.

Separado del endpoint para poder probar la aritmética sin abrir un video.
"""

FPS_POR_DEFECTO = 30.0
# Para envolver por dónde camina la gente no hacen falta 120 inferencias: con
# unas decenas repartidas sale el mismo polígono. Cada muestra de más cuesta
# una inferencia (~72 ms) y, en videos grandes, un salto de frame caro.
MUESTRAS_MAXIMAS = 40


def indices_de_muestreo(total_frames, fps, segundos, sample_fps, maximo=MUESTRAS_MAXIMAS):
    """Índices de frame a analizar, ascendentes y dentro del video.

    `fps` puede venir en 0 si la metadata del archivo está rota; en ese caso se
    asume 30 y el muestreo sigue siendo razonable.

    `maximo` acota cuántos frames se analizan: si el muestreo da más, se
    reparten uniformemente por todo el tramo en vez de recortarlo al principio.
    """
    if total_frames <= 0:
        return []
    if fps <= 0:
        fps = FPS_POR_DEFECTO
    paso = max(int(round(fps / sample_fps)), 1)
    limite = min(int(fps * segundos), total_frames)
    indices = list(range(0, limite, paso))
    if maximo and len(indices) > maximo:
        # Reparte: coger los primeros `maximo` miraría solo el arranque del video.
        salto = len(indices) / maximo
        indices = [indices[int(i * salto)] for i in range(maximo)]
    return indices
