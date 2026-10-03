# tests/test_fase68_revision_tecnica.py
import pytest

def test_documento_tecnico_contiene_datos_reales_primer_piloto():
    with open("docs/tecnico.md", "r", encoding="utf-8") as f:
        contenido = f.read()
    # El documento revisado debe mencionar la métrica del rubro
    assert "metrica_principal" in contenido, \
        "docs/tecnico.md debe mencionar la métrica del rubro (tenancy/rubros.py)"
    # Debe mencionar error medido (referencia a analytics/precision.py o Fase 5/10)
    assert "error" in contenido.lower(), \
        "docs/tecnico.md debe mencionar el error medido con datos reales"
    # Debe mencionar retención aplicada
    assert "retencion" in contenido.lower(), \
        "docs/tecnico.md debe mencionar retención aplicada"
    # Debe hacer referencia al primer piloto / primer local con datos reales
    assert ("primer local" in contenido.lower() or 
            "primer piloto" in contenido.lower() or
            "primer día" in contenido.lower()), \
        "docs/tecnico.md debe incluir datos reales del primer piloto"

def test_cartel_privacidad_contiene_datos_primer_dia():
    with open("docs/cartel-privacidad.md", "r", encoding="utf-8") as f:
        contenido = f.read()
    # El cartel debe incluir datos del primer día
    assert ("primer dia" in contenido.lower() or 
            "primer día" in contenido.lower() or
            "primer piloto" in contenido.lower() or
            "primer local" in contenido.lower()), \
        "docs/cartel-privacidad.md debe incluir datos del primer día"
