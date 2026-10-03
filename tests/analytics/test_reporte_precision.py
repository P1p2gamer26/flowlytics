import json
from pathlib import Path

from analytics.management.commands import reporte_precision as cmd_mod


def test_construye_el_reporte_desde_la_referencia(tmp_path, monkeypatch):
    referencia = {"videos": [
        {"ruta": "tienda/a.mp4", "entradas": 50, "salidas": 50, "aforo_max": None},
    ]}
    ref_path = tmp_path / "referencia.json"
    ref_path.write_text(json.dumps(referencia), encoding="utf-8")
    salida = tmp_path / "reporte.md"

    # no abrir video real: inyectar un medidor doble
    monkeypatch.setattr(cmd_mod, "medir_video",
                        lambda entry, base_dir: {"entradas": 48, "salidas": 50, "aforo_max": 3})

    cmd_mod.Command().handle(referencia=str(ref_path), salida=str(salida))

    texto = salida.read_text(encoding="utf-8")
    assert "entradas" in texto
    assert "%" in texto


def test_sin_videos_anotados_lo_dice_y_no_falla(tmp_path, monkeypatch):
    ref_path = tmp_path / "referencia.json"
    ref_path.write_text(json.dumps({"videos": [
        {"ruta": "tienda/x.mp4", "entradas": None, "salidas": None, "aforo_max": None}]}))
    salida = tmp_path / "reporte.md"
    monkeypatch.setattr(cmd_mod, "medir_video",
                        lambda entry, base_dir: (_ for _ in ()).throw(AssertionError("no medir")))

    cmd_mod.Command().handle(referencia=str(ref_path), salida=str(salida))

    assert "nada que medir" in salida.read_text(encoding="utf-8").lower()


# añadir al final de tests/analytics/test_reporte_precision.py
import pytest

from analytics.precision import MARCA_FIN, MARCA_INICIO


def _doc(tmp_path):
    ruta = tmp_path / "tecnico.md"
    ruta.write_text(f"## 4. Precisión\n\n{MARCA_INICIO}\npendiente\n{MARCA_FIN}\n\n## 5. Otra\n", encoding="utf-8")
    return ruta


def _referencia(tmp_path, videos):
    ruta = tmp_path / "referencia.json"
    ruta.write_text(json.dumps({"videos": videos}), encoding="utf-8")
    return ruta


def test_publicar_mete_el_reporte_en_el_documento_con_fecha(tmp_path, monkeypatch):
    ref = _referencia(tmp_path, [{"ruta": "t/a.mp4", "entradas": 50, "salidas": 50,
                                  "aforo_max": None}])
    doc = _doc(tmp_path)
    monkeypatch.setattr(cmd_mod, "medir_video",
                        lambda entry, base_dir: {"entradas": 48, "salidas": 50,
                                                 "aforo_max": 4})

    cmd_mod.Command().handle(referencia=str(ref), salida=str(tmp_path / "r.md"),
                             publicar=True, doc=str(doc))

    texto = doc.read_text(encoding="utf-8")
    assert "t/a.mp4" in texto
    assert "pendiente" not in texto
    assert "### Dónde falla" in texto        # el reporte entra como subsección, no como H1
    assert texto.endswith("## 5. Otra\n")    # no se comió el resto del documento
    assert "manage.py reporte_precision --publicar" in texto


def test_publicar_sin_nada_anotado_publica_que_no_hay_medicion(tmp_path, monkeypatch):
    ref = _referencia(tmp_path, [{"ruta": "t/a.mp4", "entradas": None, "salidas": None,
                                  "aforo_max": None}])
    doc = _doc(tmp_path)
    monkeypatch.setattr(cmd_mod, "medir_video",
                        lambda entry, base_dir: (_ for _ in ()).throw(AssertionError()))

    cmd_mod.Command().handle(referencia=str(ref), salida=str(tmp_path / "r.md"),
                             publicar=True, doc=str(doc))

    texto = doc.read_text(encoding="utf-8").lower()
    assert "nada que medir" in texto
    assert "0 de 1" in doc.read_text(encoding="utf-8")       # se dice cuántos, no se calla


def test_sin_publicar_no_toca_el_documento(tmp_path, monkeypatch):
    ref = _referencia(tmp_path, [{"ruta": "t/a.mp4", "entradas": 50, "salidas": 50,
                                  "aforo_max": None}])
    doc = _doc(tmp_path)
    antes = doc.read_text(encoding="utf-8")
    monkeypatch.setattr(cmd_mod, "medir_video",
                        lambda entry, base_dir: {"entradas": 50, "salidas": 50})

    cmd_mod.Command().handle(referencia=str(ref), salida=str(tmp_path / "r.md"),
                             publicar=False, doc=str(doc))

    assert doc.read_text(encoding="utf-8") == antes


def test_publicar_en_un_documento_sin_marcas_falla_y_no_lo_corrompe(tmp_path, monkeypatch):
    ref = _referencia(tmp_path, [{"ruta": "t/a.mp4", "entradas": 50, "salidas": 50,
                                  "aforo_max": None}])
    doc = tmp_path / "tecnico.md"
    doc.write_text("# Sin marcas\n", encoding="utf-8")
    monkeypatch.setattr(cmd_mod, "medir_video",
                        lambda entry, base_dir: {"entradas": 50, "salidas": 50})

    with pytest.raises(ValueError):
        cmd_mod.Command().handle(referencia=str(ref), salida=str(tmp_path / "r.md"),
                                 publicar=True, doc=str(doc))
    assert doc.read_text(encoding="utf-8") == "# Sin marcas\n"
