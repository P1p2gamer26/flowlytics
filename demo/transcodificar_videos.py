import cv2, glob, io, os, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TARGET_FPS = {"court_sq.ogv": 30.0, "pasillo_aeropuerto.webm": 30.0, "bluewater.webm": 24.0}
CAP_FRAMES = 120_000  # corta el bucle si la metadata miente
# H.264: los videos se sirven al editor de zonas y ningún navegador reproduce
# mp4v (MPEG-4 Part 2), aunque OpenCV lo lea sin problema.
FOURCC = "avc1"


def apto_para_navegador(ruta):
    with open(ruta, "rb") as f:
        return b"avc1" in f.read()

for p in sorted(glob.glob("demo/videos/**/*.*", recursive=True)):
    if not p.endswith((".webm", ".ogv", ".mp4")):
        continue
    nombre = os.path.basename(p)
    base = os.path.splitext(nombre)[0]
    destino = os.path.join(os.path.dirname(p), f"{base}.mp4")
    if os.path.exists(destino) and apto_para_navegador(destino):
        print(f"{nombre}: ya existe {base}.mp4 en H.264, salto")
        continue
    # Escribe a un temporal: el destino puede ser el archivo que estamos
    # leyendo (reconversión in-place de un mp4v viejo).
    tmp = destino + ".tmp.mp4"
    fps = TARGET_FPS.get(nombre, 30.0)
    cap = cv2.VideoCapture(p)
    writer = None
    n = 0
    while n < CAP_FRAMES:
        ok, frame = cap.read()
        if not ok:
            break
        if writer is None:
            h, w = frame.shape[:2]
            writer = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*FOURCC), fps, (w, h))
        writer.write(frame)
        n += 1
    cap.release()
    if writer is None:
        print(f"{nombre}: no se pudo leer frames, NO transcode")
        continue
    writer.release()
    if not apto_para_navegador(tmp):
        os.remove(tmp)
        print(f"{nombre}: el encoder no produjo H.264, se deja como estaba")
        continue
    os.replace(tmp, destino)
    print(f"{nombre}: {n} frames -> {base}.mp4 @ {fps:g} fps ({FOURCC})")
