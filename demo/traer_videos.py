#!/usr/bin/env python3
"""Trae el banco de video de prueba. Es el UNICO corpus del proyecto.

    python demo/traer_videos.py

Son tres camaras fijas en tiendas reales. Sustituyen al corpus anterior, que se
audito el 6-sep-2026 y resulto no parecerse al caso de uso: una pelicula en
blanco y negro de archivo, un video de celular grabado caminando por un mall, un
pasillo de metro y un CCTV lavado donde la gente eran motas. Medir con aquello
describia un escenario que no existe en produccion — ver
docs/notas/auditoria-corpus-6sep.md.

Los .mp4 no se versionan (pesan ~90 MB); este script los reconstruye.
"""
import subprocess
import sys
from pathlib import Path

DESTINO = Path(__file__).resolve().parent / "videos" / "cctv"

# `bv*[vcodec^=avc1]` no es opcional: sin el, YouTube entrega AV1 y el OpenCV de
# la VM .28 no lo decodifica — el archivo baja entero, pesa lo que debe, y
# `cap.read()` devuelve vacio sin decir por que.
FORMATO = "bv*[vcodec^=avc1][height<=1080]/b[vcodec^=avc1]"

VIDEOS = [
    ("tienda_usa", "https://www.youtube.com/watch?v=-1bRhYjw1qE",
     "Tienda en EEUU, camara de esquina alta"),
    ("tienda_iprox", "https://www.youtube.com/watch?v=KMJS66jBtVQ",
     "Tienda pequena con caja y pasillos: la mas parecida al cliente objetivo"),
    ("super_caja", "https://www.youtube.com/watch?v=-8zyEwAa50Q",
     "Caja de supermercado en vista alta: fila y tiempo de espera"),
]


def main() -> int:
    DESTINO.mkdir(parents=True, exist_ok=True)
    faltan = []

    for nombre, url, que_es in VIDEOS:
        destino = DESTINO / f"{nombre}.mp4"
        if destino.exists():
            print(f"  ya esta: {nombre}.mp4")
            continue
        print(f"  bajando {nombre} — {que_es}")
        r = subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--no-warnings", "-f", FORMATO,
             "-o", str(destino), url],
            capture_output=True, text=True)
        if r.returncode != 0 or not destino.exists():
            faltan.append(nombre)
            print(f"    fallo: {r.stderr.strip().splitlines()[-1:] or r.returncode}")

    if faltan:
        print(f"\nNo se pudieron traer: {', '.join(faltan)}")
        print("Si yt-dlp se queja de formatos, actualizalo: pip install -U yt-dlp")
        return 1

    print(f"\nBanco listo en {DESTINO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
