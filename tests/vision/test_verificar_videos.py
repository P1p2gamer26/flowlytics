"""Un mp4 que el navegador no puede reproducir tiene que delatarse."""
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from vision.core.codecs import es_h264


def _video(ruta, fourcc):
    w = cv2.VideoWriter(str(ruta), cv2.VideoWriter_fourcc(*fourcc), 25, (64, 48))
    for i in range(6):
        w.write(np.full((48, 64, 3), i * 40, dtype=np.uint8))
    w.release()


def _hay_encoder_h264():
    """OpenCV solo escribe avc1 si su ffmpeg trae un encoder H.264. El de la VM
    de la Javeriana no lo trae (busca h264_v4l2m2m, que necesita hardware que
    ahí no existe), y eso es una carencia del entorno, no del código."""
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / "sonda.mp4"
        _video(ruta, "avc1")
        return es_h264(ruta)


@pytest.mark.skipif(not _hay_encoder_h264(),
                    reason="El OpenCV de este entorno no sabe codificar H.264.")
def test_reconoce_un_h264(tmp_path):
    ruta = tmp_path / "bueno.mp4"
    _video(ruta, "avc1")
    assert es_h264(ruta) is True


def test_delata_un_mp4v(tmp_path):
    ruta = tmp_path / "malo.mp4"
    _video(ruta, "mp4v")
    assert es_h264(ruta) is False


def test_un_archivo_que_no_existe_no_es_h264(tmp_path):
    assert es_h264(tmp_path / "no_existe.mp4") is False
