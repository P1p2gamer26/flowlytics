import cv2, glob, io, os, sys
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.conf import settings
from vision.core.detector import YoloDetector

detector = YoloDetector(settings.DETECTOR_MODEL, settings.DETECTOR_IMGSZ, settings.DETECTOR_DEVICE)

for p in sorted(glob.glob("demo/videos/**/*.mp4", recursive=True)):
    cap = cv2.VideoCapture(p)
    total = Counter()
    muestras = 0
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i % 60 == 0:  # una muestra cada 2 s a 30 fps
            dets = detector.detect(frame)
            clases = Counter(dets["class_name"].tolist())
            for k, v in clases.items():
                total[k] += v
            muestras += 1
        i += 1
    cap.release()
    print(f"{os.path.basename(p):26s} muestras={muestras:4d} personas_por_muestra~{total.get('person',0)/max(muestras,1):.1f} detalle={dict(total)}")
