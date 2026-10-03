# tests/test_fase35_acumulador.py
import pytest
from vision.core.events import avisos_sin_duplicados

def test_acumulador_no_duplicados():
    eventos = [
        {"tipo": "long_queue", "minutos": 15},
        {"tipo": "long_queue", "minutos": 15},  # duplicado
        {"tipo": "empty_counter", "minutos": 10},
    ]
    unicos = avisos_sin_duplicados(eventos)
    assert len(unicos) == 2
    assert unicos[0]["tipo"] == "long_queue"
