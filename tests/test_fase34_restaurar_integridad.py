import os, tarfile, tempfile
import pytest
from django.core.management import call_command
from io import StringIO

TEST_BACKUP = "tests/temp_backups/respaldo_2026-09-16_120000.tar.gz"

def test_restaurar_respaldo_verifica_integridad():
    # Asume respaldo creado en paso anterior
    if not os.path.exists(TEST_BACKUP):
        pytest.skip("Falta respaldo de prueba")
    out = StringIO()
    call_command("restaurar_respaldo", TEST_BACKUP, stdout=out)
    output = out.getvalue()
    assert "Integridad verificada" in output or "OK" in output
