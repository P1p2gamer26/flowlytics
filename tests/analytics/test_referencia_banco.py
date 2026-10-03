"""El banco de video que sí está versionado: su anotación.

demo/videos/ está en .gitignore (los videos pesan) pero demo/referencia.json no:
es el archivo que dice cuál es la verdad de cada video. Si se rompe su forma, el
reporte de precisión mide contra basura sin avisar.
"""
import json
from pathlib import Path

from django.conf import settings

from analytics.precision import METRICAS

REFERENCIA = Path(settings.BASE_DIR) / "demo" / "referencia.json"


def _videos():
    return json.loads(REFERENCIA.read_text(encoding="utf-8"))["videos"]


def test_cada_entrada_tiene_lo_que_el_medidor_le_pide():
    for entry in _videos():
        assert entry["ruta"], "una entrada sin ruta no se puede medir"
        # ancho y alto escalan la línea de conteo: si faltan, la línea se desplaza
        assert entry.get("ancho") and entry.get("alto"), f"{entry['ruta']} sin tamaño"
        assert entry.get("fps"), f"{entry['ruta']} sin fps"
        for metrica in METRICAS:
            assert metrica in entry, f"{entry['ruta']} sin la clave {metrica}"
        assert isinstance(entry.get("lineas", []), list)


def test_no_hay_rutas_repetidas():
    rutas = [e["ruta"] for e in _videos()]
    assert len(rutas) == len(set(rutas))


def test_un_video_anotado_trae_las_lineas_sobre_las_que_contar():
    # anotar entradas/salidas sin línea es contar cruces de una línea que no existe:
    # el reporte daría 100% de error y parecería culpa del detector
    for entry in _videos():
        if entry.get("entradas") is not None or entry.get("salidas") is not None:
            assert entry.get("lineas"), (
                f"{entry['ruta']} tiene conteo anotado pero ninguna línea: "
                "manage.py anotar_referencia no llena 'lineas', se dibujan a mano")
