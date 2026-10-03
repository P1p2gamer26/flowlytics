"""El polígono sugerido envuelve por dónde caminó la gente."""
import cv2
import numpy as np

from vision.core.sugerencia import poligono_sugerido


def test_sin_puntos_no_hay_sugerencia():
    assert poligono_sugerido([], (640, 480)) is None


def test_menos_de_tres_puntos_no_alcanza_para_un_poligono():
    assert poligono_sugerido([(10, 10), (20, 20)], (640, 480), minimo=3) is None


def test_unas_pocas_detecciones_no_bastan_para_una_zona():
    # tres puntos dan un triángulo diminuto: geometría válida, sugerencia inútil
    pocos = [(600, 120), (750, 150), (1070, 450)]
    assert poligono_sugerido(pocos, (1280, 720)) is None
    assert poligono_sugerido(pocos, (1280, 720), minimo=3) is not None


def test_envuelve_la_nube_de_puntos():
    # gente caminando dentro de un rectángulo de 100..300 x 200..400
    puntos = [(x, y) for x in range(100, 301, 10) for y in range(200, 401, 10)]
    poly = poligono_sugerido(puntos, (640, 480))

    assert len(poly) >= 3
    assert all(len(p) == 2 and all(isinstance(c, int) for c in p) for p in poly)
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    assert min(xs) >= 95 and max(xs) <= 305
    assert min(ys) >= 195 and max(ys) <= 405
    # y de verdad cubre el interior de la nube, no es una astilla
    area = cv2.contourArea(np.array(poly, dtype=np.int32))
    assert area > 0.6 * (200 * 200)


def test_un_punto_perdido_no_estira_la_zona():
    # una nube densa arriba a la izquierda y UN paseante en la esquina opuesta
    nube = [(x, y) for x in range(100, 201, 5) for y in range(100, 201, 5)]
    poly = poligono_sugerido(nube + [(1200, 700)], (1280, 720))

    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    assert max(xs) < 400, "el punto aislado estiró el polígono a lo ancho"
    assert max(ys) < 400, "el punto aislado estiró el polígono a lo alto"


def test_no_descarta_una_nube_legitimamente_dispersa():
    # dos grupos reales y separados: los dos tienen que quedar dentro
    izq = [(x, y) for x in range(100, 161, 5) for y in range(100, 161, 5)]
    der = [(x, y) for x in range(900, 961, 5) for y in range(600, 661, 5)]
    poly = poligono_sugerido(izq + der, (1280, 720))

    xs = [p[0] for p in poly]
    assert max(xs) > 850, "descartó un grupo entero, no un punto suelto"


def test_recorta_a_los_limites_del_frame():
    puntos = [(-50, -50), (700, -20), (700, 500), (-50, 500), (300, 250)]
    poly = poligono_sugerido(puntos, (640, 480), minimo=3)

    assert all(0 <= x <= 640 and 0 <= y <= 480 for x, y in poly)


import supervision as sv

from vision.core.sugerencia import recorrido_de_video


class DetectorDePrueba:
    """Devuelve siempre una caja fija: no carga YOLO ni mira el frame."""

    def detect(self, frame):
        return sv.Detections(xyxy=np.array([[10.0, 20.0, 30.0, 60.0]]))


def _clip(ruta, frames=10, ancho=64, alto=48, fps=5.0):
    writer = cv2.VideoWriter(str(ruta), cv2.VideoWriter_fourcc(*"mp4v"), fps, (ancho, alto))
    for i in range(frames):
        writer.write(np.full((alto, ancho, 3), (i * 10) % 256, dtype=np.uint8))
    writer.release()


def test_recorrido_devuelve_pies_y_tamano_del_frame(tmp_path):
    video = tmp_path / "clip.mp4"
    _clip(video)

    puntos, ancho, alto = recorrido_de_video(str(video), DetectorDePrueba(),
                                             segundos=60, sample_fps=2.0)

    assert (ancho, alto) == (64, 48)
    assert puntos                      # una muestra, un par de pies
    assert puntos[0] == [20, 60]       # centro-abajo de la caja
    assert all(isinstance(c, int) for p in puntos for c in p)


def test_recorrido_respeta_el_presupuesto_de_muestras(tmp_path):
    video = tmp_path / "largo.mp4"
    _clip(video, frames=40)

    puntos, _, _ = recorrido_de_video(str(video), DetectorDePrueba(),
                                      segundos=60, sample_fps=5.0, maximo=3)

    assert len(puntos) == 3


def test_un_video_que_no_abre_no_revienta(tmp_path):
    falso = tmp_path / "no-es-video.mp4"
    falso.write_bytes(b"basura")

    puntos, ancho, alto = recorrido_de_video(str(falso), DetectorDePrueba(),
                                             segundos=60, sample_fps=2.0)

    assert puntos == []
