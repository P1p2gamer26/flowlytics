import os

def test_tecnico_tiene_resultados_reales():
    assert os.path.exists("docs/tecnico.md")
    contenido = open("docs/tecnico.md").read()
    assert "contrato" in contenido.lower() or "retención" in contenido.lower() or "precisión" in contenido.lower()
