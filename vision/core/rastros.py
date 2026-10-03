"""Rastros dibujables derivados del snapshot de detecciones.

`pie_de_caja` es el único origen de coordenadas: el mapa de calor y este rastro
describen dónde pisa la misma persona, no el pecho en una vista y los pies en otra.
"""
from vision.core.geometria import pie_de_caja

def rastros_de_pistas(pistas):
    """Agrupa las cajas del último análisis por id, sin unir ids distintos."""
    por_id = {}
    for instante in pistas:
        for caja in instante.get("cajas", []):
            track_id = caja["id"]
            x, y = pie_de_caja(caja["xyxy"])
            por_id.setdefault(track_id, []).append(
                {"t": instante["t"], "xy": [x, y]})
    return [{"track_id": track_id, "puntos": puntos}
            for track_id, puntos in por_id.items()]
