"""Invariantes que ninguna tarea individual protege por sí sola."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def test_vision_core_does_not_import_django():
    """vision/core debe ser testeable sin Django; si importa Django, se rompió."""
    for path in (ROOT / "vision" / "core").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "import django" not in source, path
        assert "from django" not in source, path


def test_no_frame_is_written_outside_the_clip_path():
    """Ningún módulo de vision escribe imágenes a disco, salvo vision/anotar.py
    que es la función intentionally-exception para la prueba de humo."""
    forbidden = ("cv2.imwrite", "Image.save")
    excepciones = {ROOT / "vision" / "anotar.py"}
    for path in (ROOT / "vision").rglob("*.py"):
        if path in excepciones:
            continue
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source, f"{path} escribe frames a disco"


@pytest.mark.django_db
def test_purge_command_runs():
    from django.core.management import call_command
    call_command("purge_clips")
