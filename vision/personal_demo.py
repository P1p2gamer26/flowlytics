"""Clasificación TRABAJADOR vs CLIENTE en capa Personas.

Funciones puras sin Django: solo numpy, cv2, json, pathlib.
"""
import json
import os
from pathlib import Path

import cv2
import numpy as np


def _normalizar_poligonos(poligonos_px, ref_wh):
    """Convierte polígonos en píxeles a coordenadas normalizadas [0,1]."""
    if not poligonos_px:
        return []
    w, h = ref_wh
    norm = []
    for poly in poligonos_px:
        arr = np.array(poly, dtype=float)
        arr[:, 0] /= w
        arr[:, 1] /= h
        norm.append(arr)
    return norm


def cargar_regiones(source: str, zonas_staff=(), ref_wh=None) -> list[np.ndarray]:
    """Carga regiones de personal desde demo/regiones_personal.json.

    Args:
        source: Ruta o nombre del archivo de video (se usa basename).
        zonas_staff: Lista de polígonos en píxeles (respecto a ref_wh) para añadir.
        ref_wh: Tupla (width, height) de referencia. Si None, usa la del JSON.

    Returns:
        Lista de polígonos normalizados [0,1] como np.ndarray.
    """
    repo_root = Path(__file__).resolve().parents[1]
    json_path = repo_root / "demo" / "regiones_personal.json"

    regiones = []
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        ref_json = data.get("ref", [854, 480])
        key = os.path.basename(source)
        regiones_json = data.get("regiones", {}).get(key, [])

        # Los polígonos del JSON están en píxeles de SU referencia, no la de la cámara.
        regiones = _normalizar_poligonos(regiones_json, tuple(ref_json))

    if zonas_staff:
        if ref_wh is None:
            raise ValueError("ref_wh requerido cuando hay zonas_staff")
        regiones.extend(_normalizar_poligonos(zonas_staff, ref_wh))

    return regiones


def es_trabajador(xyxy, regiones_norm, frame_wh) -> bool:
    """Determina si una detección es trabajador según su pie de caja."""
    from vision.core.geometria import pie_de_caja

    x, y = pie_de_caja(xyxy)
    w, h = frame_wh
    punto_norm = (x / w, y / h)

    return any(cv2.pointPolygonTest(np.asarray(poly, np.float32), punto_norm, False) >= 0
               for poly in regiones_norm)


def clasificar(xyxy_list, regiones_norm, frame_wh) -> list[bool]:
    """Clasifica una lista de cajas como trabajador (True) o cliente (False)."""
    return [es_trabajador(xyxy, regiones_norm, frame_wh) for xyxy in xyxy_list]


def pintar_roles(frame, xyxy_list, roles) -> np.ndarray:
    """Pinta cajas y etiquetas según rol: trabajador (azul) o cliente (verde).

    Args:
        frame: Imagen BGR (numpy array).
        xyxy_list: Lista de cajas [x1, y1, x2, y2].
        roles: Lista de bool (True=trabajador, False=cliente).

    Returns:
        Copia del frame con anotaciones.
    """
    out = frame.copy()
    h, w = out.shape[:2]

    # Colores BGR
    COLOR_TRABAJADOR = (201, 99, 37)   # #2563c9
    COLOR_CLIENTE = (87, 122, 15)      # #0f7a57
    COLOR_TEXTO = (255, 255, 255)
    FONT = cv2.FONT_HERSHEY_SIMPLEX
    # Proporcional al ancho: en la tarjeta el frame se ve a ~1/3, con 0.6 fijo no se leía.
    k = max(1.0, w / 640)
    ESCALA = 0.6 * k
    ESPESOR_CAJA = max(3, round(2 * k))
    ESPESOR_TEXTO = max(2, round(1.5 * k))

    trabajadores = sum(1 for r in roles if r)
    clientes = len(roles) - trabajadores

    for xyxy, es_trab in zip(xyxy_list, roles):
        x1, y1, x2, y2 = map(int, xyxy)
        color = COLOR_TRABAJADOR if es_trab else COLOR_CLIENTE
        label = "Trabajador" if es_trab else "Cliente"

        # Caja
        cv2.rectangle(out, (x1, y1), (x2, y2), color, ESPESOR_CAJA)

        # Etiqueta sobre la caja
        (tw, th), baseline = cv2.getTextSize(label, FONT, ESCALA, ESPESOR_TEXTO)
        tx1 = max(0, min(x1, w - tw - 6))
        ty1 = max(th + baseline + 4, min(y1 - 4, h - th - baseline - 4))

        cv2.rectangle(out, (tx1, ty1 - th - baseline - 2), (tx1 + tw + 4, ty1 + 2), color, -1)
        cv2.putText(out, label, (tx1 + 2, ty1 - baseline), FONT, ESCALA, COLOR_TEXTO, ESPESOR_TEXTO, cv2.LINE_AA)

    # Rótulo ASCII en esquina superior izquierda
    rotulo = f"{clientes} clientes | {trabajadores} trabajadores"
    (rw, rh), base = cv2.getTextSize(rotulo, FONT, ESCALA, ESPESOR_TEXTO)
    pad = round(8 * k)
    cv2.rectangle(out, (0, 0), (rw + 2 * pad, rh + base + 2 * pad), (0, 0, 0), -1)
    cv2.putText(out, rotulo, (pad, pad + rh), FONT, ESCALA, COLOR_TEXTO, ESPESOR_TEXTO, cv2.LINE_AA)

    return out