"""Puntos que se leen de una caja detectada.

Sin Django, sin video: recibe numeros y devuelve numeros. Comparten origen la
Fase 15 (mapa de calor) y la Fase 17 (recorridos dibujados, sin plan
todavia): las dos necesitan EL MISMO punto por persona, y si cada una eligiera
el suyo (una el centro, otra el pie) las dos vistas contarian una historia
distinta del mismo video.
"""

def pie_de_caja(xyxy) -> tuple[float, float]:
    """El punto donde la persona pisa: centro del borde inferior de su caja.

    No el centro geometrico de la caja — ese flota a la altura del pecho y se
    despega del suelo en cuanto alguien se acerca a la camara (la caja crece
    hacia arriba mas que hacia los lados).
    """
    x1, y1, x2, y2 = xyxy
    return ((x1 + x2) / 2, float(y2))
