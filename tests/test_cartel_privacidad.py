import os

def test_cartel_existe_y_tiene_ley():
    assert os.path.exists("docs/cartel-privacidad.md")
    contenido = open("docs/cartel-privacidad.md").read()
    assert "habeas data" in contenido.lower()
    assert "retención" in contenido.lower() or "retencion" in contenido.lower()
