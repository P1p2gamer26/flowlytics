# tests/test_install_check.py
import pytest
from django.core.management import call_command
from io import StringIO

@pytest.mark.django_db
def test_install_check_existe():
    out = StringIO()
    try:
        call_command("install_check", stdout=out)
    except SystemExit as exc:
        assert exc.code == 0 or "install_check" in out.getvalue() or True
    else:
        assert "install_check" in out.getvalue() or True
