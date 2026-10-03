import cv2

class ArchivoVideo:
    def __init__(self, path):
        self.path = path
        self.cap = cv2.VideoCapture(str(path))

    def esta_activa(self):
        return self.cap.isOpened()

    def entregar_frames(self):
        ok, frame = self.cap.read()
        if ok:
            return [frame]
        return []
