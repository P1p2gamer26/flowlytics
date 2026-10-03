import pytest
from unittest.mock import patch
from django.core.management import call_command

@pytest.mark.django_db
def test_humo_con_doble_rtsp():
    with patch("vision.core.fuente_video.FuenteVideo") as Doble:
        instancia = Doble.return_value
        instancia.esta_activa.return_value = True
        instancia.entregar_frames.return_value = [None] * 3
        # Correr el ciclo completo con la fuente simulada
        call_command("humo", "rtsp://doble/local")
        # Confirmar que el resumen existe y es coherente
        from vision.models import ResumenDia
        assert ResumenDia.objects.exists()
