"""Qué frames se analizan: los justos, no todos."""
from vision.core.muestreo import indices_de_muestreo


def test_toma_sample_fps_frames_por_segundo():
    # 30 fps, 10 s de video, muestreando a 2 FPS -> 20 frames
    idx = indices_de_muestreo(total_frames=300, fps=30.0, segundos=10, sample_fps=2.0)
    assert len(idx) == 20
    assert idx[:3] == [0, 15, 30]


def test_no_pasa_del_final_del_video():
    # se piden 60 s pero el video solo tiene 100 frames (~3.3 s)
    idx = indices_de_muestreo(total_frames=100, fps=30.0, segundos=60, sample_fps=2.0)
    assert idx[-1] < 100
    assert all(0 <= i < 100 for i in idx)


def test_ascendentes_y_sin_repetidos():
    idx = indices_de_muestreo(total_frames=1000, fps=25.0, segundos=40, sample_fps=2.0)
    assert idx == sorted(idx)
    assert len(idx) == len(set(idx))


def test_fps_invalido_no_revienta():
    # metadata rota: fps 0. Debe caer en algo razonable, no dividir por cero.
    idx = indices_de_muestreo(total_frames=100, fps=0.0, segundos=10, sample_fps=2.0)
    assert len(idx) > 0
    assert all(0 <= i < 100 for i in idx)


def test_acota_cuantos_frames_se_analizan():
    # 60 s a 30 fps muestreando a 2 FPS darían 120: se quedan en el presupuesto
    idx = indices_de_muestreo(total_frames=1800, fps=30.0, segundos=60,
                              sample_fps=2.0, maximo=40)
    assert len(idx) == 40
    assert idx == sorted(idx)
    assert len(idx) == len(set(idx))


def test_las_muestras_se_reparten_por_todo_el_tramo():
    # coger los primeros 40 miraría solo los primeros segundos del video
    idx = indices_de_muestreo(total_frames=1800, fps=30.0, segundos=60,
                              sample_fps=2.0, maximo=40)
    assert idx[-1] > 1500, "el muestreo se quedó en el arranque del video"


def test_sin_presupuesto_no_recorta():
    idx = indices_de_muestreo(total_frames=1800, fps=30.0, segundos=60,
                              sample_fps=2.0, maximo=None)
    assert len(idx) == 120


def test_video_vacio_no_da_indices():
    assert indices_de_muestreo(total_frames=0, fps=30.0, segundos=10, sample_fps=2.0) == []
