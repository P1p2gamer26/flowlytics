"""Propone un polígono a partir de por dónde caminó la gente.

Sugiere geometría, no significado: sabe decir "aquí pasa gente", no si eso es
una fila o una caja. El nombre y el tipo los pone la persona.
"""
import cv2
import numpy as np
import supervision as sv

from vision.core.muestreo import MUESTRAS_MAXIMAS, indices_de_muestreo

# Con menos de esto la envolvente es una astilla que no describe nada: tres
# detecciones sueltas dan un triángulo diminuto, no una zona.
MUESTRAS_MINIMAS = 20
# Un punto sin vecinos cerca es alguien que cruzó una vez por el borde, no una
# zona de paso. El radio sale del tamaño del frame para que valga igual en
# 352x288 que en 1280x720.
FRACCION_RADIO = 0.15
VECINOS_MINIMOS = 3


def _sin_aislados(puntos, radio, vecinos):
    """Quita los puntos con menos de `vecinos` compañeros dentro de `radio`."""
    arr = np.array(puntos, dtype=float)
    # ponytail: distancias todos-contra-todos, O(n²). Con unos miles de puntos
    # sobra; si se muestrea mucho más denso, usar una rejilla espacial.
    d = np.linalg.norm(arr[:, None, :] - arr[None, :, :], axis=-1)
    acompanados = (d <= radio).sum(axis=1) - 1   # sin contarse a sí mismo
    return arr[acompanados >= vecinos]


def recorrido_de_video(entrada, detector, segundos, sample_fps, maximo=MUESTRAS_MAXIMAS):
    """Por dónde caminó la gente en los primeros `segundos` de video.

    Devuelve ([[x, y], ...], ancho, alto): los pies de cada detección y el tamaño
    del frame. Salta al frame que toca en vez de decodificar los intermedios, así
    el coste es el número de muestras y no la duración del video.

    `detector` es cualquier cosa con `.detect(frame)`; en los tests, un doble.
    Un archivo ilegible devuelve la lista vacía: quien llame decide qué decir.
    """
    cap = cv2.VideoCapture(entrada)
    pies = []
    ancho = alto = 0
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        for i in indices_de_muestreo(total, fps, segundos, sample_fps, maximo):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ok, frame = cap.read()
            if not ok:
                break
            dets = detector.detect(frame)
            pies.extend(dets.get_anchors_coordinates(sv.Position.BOTTOM_CENTER).tolist())
    finally:
        cap.release()
    return [[int(x), int(y)] for x, y in pies], ancho, alto


def poligono_sugerido(puntos, frame_wh, minimo=MUESTRAS_MINIMAS,
                      radio=None, vecinos=VECINOS_MINIMOS):
    """Envolvente de `puntos` [(x, y), ...], recortada al frame.

    Descarta antes los puntos aislados: un peatón que cruza una esquina no
    debería estirar la zona hasta allá.

    Devuelve [[x, y], ...] con al menos 3 vértices, o None si no hay material.
    """
    if len(puntos) < max(minimo, 3):
        return None

    w, h = frame_wh
    if radio is None:
        radio = FRACCION_RADIO * max(w, h)
    densos = _sin_aislados(puntos, radio, vecinos)
    # Si el filtro se lleva casi todo, la nube entera era dispersa: mejor la
    # envolvente de siempre que ninguna sugerencia.
    if len(densos) < 3:
        densos = np.array(puntos, dtype=float)

    hull = cv2.convexHull(densos.astype(np.int32))
    # Simplifica: sin esto el hull trae decenas de vértices casi colineales.
    epsilon = 0.01 * cv2.arcLength(hull, True)
    poly = cv2.approxPolyDP(hull, epsilon, True).reshape(-1, 2)
    if len(poly) < 3:
        return None

    poly[:, 0] = np.clip(poly[:, 0], 0, w)
    poly[:, 1] = np.clip(poly[:, 1], 0, h)
    return [[int(x), int(y)] for x, y in poly]
