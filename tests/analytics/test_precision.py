from analytics.precision import error_pct, calcular_error, resumen, generar_reporte


def test_error_pct_basico():
    assert error_pct(90, 100) == 10.0
    assert error_pct(110, 100) == 10.0        # sobreconteo también es error


def test_error_pct_referencia_cero():
    assert error_pct(0, 0) == 0.0
    assert error_pct(3, 0) == 100.0           # contó de más donde no había nada


def test_calcular_error_ignora_metricas_sin_anotar():
    medido = {"entradas": 48, "salidas": 50, "aforo_max": 7}
    referencia = {"entradas": 50, "salidas": 50, "aforo_max": None}
    err = calcular_error(medido, referencia)
    assert set(err) == {"entradas", "salidas"}     # aforo_max sin anotar se omite
    assert err["entradas"] == 4.0
    assert err["salidas"] == 0.0


def test_resumen_promedia_por_metrica():
    resultados = [
        {"video": "a", "errores": {"entradas": 10.0, "salidas": 0.0}},
        {"video": "b", "errores": {"entradas": 20.0}},
    ]
    prom = resumen(resultados)
    assert prom["entradas"] == 15.0
    assert prom["salidas"] == 0.0


def test_generar_reporte_usa_el_medidor_inyectado():
    referencia = {"videos": [
        {"ruta": "tienda/a.mp4", "entradas": 50, "salidas": 50, "aforo_max": None},
        {"ruta": "tienda/sin_anotar.mp4", "entradas": None, "salidas": None, "aforo_max": None},
    ]}
    medidor = lambda entry: {"entradas": 48, "salidas": 50, "aforo_max": 7}

    texto, resultados = generar_reporte(referencia, medidor)

    # solo se evalúa el video anotado
    assert len(resultados) == 1
    assert resultados[0]["video"] == "tienda/a.mp4"
    assert "entradas" in texto and "%" in texto
    assert "sin_anotar" not in texto or "omitido" in texto.lower()


from types import SimpleNamespace

from analytics.precision import medir_desde_ventanas


def _ventana(crossings, occupancy_max):
    """Un WindowSummary de mentira: medir_desde_ventanas solo lee estos dos campos."""
    return SimpleNamespace(crossings=crossings, occupancy_max=occupancy_max)


def test_medir_desde_ventanas_suma_cruces_de_todas_las_lineas():
    ventanas = [_ventana({"puerta": (10, 8), "pasillo": (2, 1)}, {"todo": 4})]
    assert medir_desde_ventanas(ventanas) == {"entradas": 12, "salidas": 9, "aforo_max": 4}


def test_medir_desde_ventanas_suma_entre_ventanas_pero_el_aforo_es_el_maximo():
    ventanas = [_ventana({"puerta": (10, 0)}, {"todo": 7}),
                _ventana({"puerta": (5, 3)}, {"todo": 3})]
    # el aforo máximo no se suma: 7 y 3 simultáneos no son 10 simultáneos
    assert medir_desde_ventanas(ventanas) == {"entradas": 15, "salidas": 3, "aforo_max": 7}


def test_medir_desde_ventanas_sin_ventanas_no_revienta():
    assert medir_desde_ventanas([]) == {"entradas": 0, "salidas": 0, "aforo_max": 0}


def test_medir_desde_ventanas_con_zonas_vacias_da_aforo_cero_no_un_error():
    # un video sin zonas no puede reportar aforo; que lo diga con 0, sin explotar
    assert medir_desde_ventanas([_ventana({}, {})])["aforo_max"] == 0


# añadir al final de tests/analytics/test_precision.py
from analytics.precision import UMBRAL_FALLA, sin_anotar


def test_sin_anotar_lista_los_videos_que_no_se_pueden_medir():
    referencia = {"videos": [
        {"ruta": "a.mp4", "entradas": 5, "salidas": 5, "aforo_max": None},
        {"ruta": "b.mp4", "entradas": None, "salidas": None, "aforo_max": None},
        {"ruta": "c.mp4", "entradas": None, "salidas": None, "aforo_max": 3},
    ]}
    assert sin_anotar(referencia) == ["b.mp4"]      # basta una métrica para contar como anotado


def test_el_reporte_dice_cuantos_videos_midio_de_cuantos():
    referencia = {"videos": [
        {"ruta": "a.mp4", "entradas": 50, "salidas": 50, "aforo_max": None},
        {"ruta": "b.mp4", "entradas": None, "salidas": None, "aforo_max": None},
    ]}
    texto, _ = generar_reporte(referencia, lambda e: {"entradas": 50, "salidas": 50})

    assert "1 de 2" in texto
    assert "b.mp4" in texto and "omitido" in texto.lower()   # no desaparece en silencio


def test_el_reporte_muestra_la_diferencia_absoluta_no_solo_el_porcentaje():
    referencia = {"videos": [{"ruta": "a.mp4", "entradas": 100, "salidas": 100,
                              "aforo_max": None}]}
    texto, _ = generar_reporte(referencia, lambda e: {"entradas": 93, "salidas": 104})

    assert "-7" in texto and "+4" in texto      # 100% sobre 2 personas no es lo mismo que sobre 200


def test_el_reporte_tiene_una_seccion_de_donde_falla():
    referencia = {"videos": [
        {"ruta": "facil.mp4", "entradas": 100, "salidas": 100, "aforo_max": None},
        {"ruta": "dificil.mp4", "entradas": 100, "salidas": 100, "aforo_max": None},
    ]}

    def medidor(entry):
        return ({"entradas": 99, "salidas": 100} if entry["ruta"] == "facil.mp4"
                else {"entradas": 40, "salidas": 100})

    texto, _ = generar_reporte(referencia, medidor)
    donde_falla = texto.split("## Dónde falla")[1]

    assert "dificil.mp4" in donde_falla            # 60% de error, muy por encima del umbral
    assert "facil.mp4" not in donde_falla          # 1% no es un caso donde falle
    assert UMBRAL_FALLA == 15.0


def test_sin_ningun_video_anotado_el_reporte_no_finge_un_numero():
    referencia = {"videos": [{"ruta": "a.mp4", "entradas": None, "salidas": None,
                              "aforo_max": None}]}
    texto, resultados = generar_reporte(
        referencia, lambda e: (_ for _ in ()).throw(AssertionError("no debe medir")))

    assert resultados == []
    assert "nada que medir" in texto.lower()
    assert "%" not in texto.split("## Promedio por métrica")[1].split("##")[0]


from analytics.precision import anotar


def test_anotar_agrega_un_video_nuevo_con_las_claves_de_conteo_vacias():
    referencia = {"videos": []}
    anotar(referencia, {"ruta": "tienda/entrada.mp4", "ancho": 640, "alto": 360})

    entrada = referencia["videos"][0]
    assert entrada["ruta"] == "tienda/entrada.mp4"
    assert entrada["ancho"] == 640
    assert entrada["entradas"] is None and entrada["salidas"] is None
    assert entrada["lineas"] == []


def test_anotar_actualiza_por_ruta_sin_duplicar():
    referencia = {"videos": [{"ruta": "a.mp4", "ancho": 640, "entradas": None}]}
    anotar(referencia, {"ruta": "a.mp4", "entradas": 42})

    assert len(referencia["videos"]) == 1
    assert referencia["videos"][0]["entradas"] == 42


def test_anotar_no_borra_lo_que_ya_estaba_anotado():
    # reanotar el conteo no puede tirar a la basura las líneas dibujadas
    referencia = {"videos": [{"ruta": "a.mp4", "lineas": [{"name": "puerta"}],
                              "entradas": 10, "notas": "cámara alta"}]}
    anotar(referencia, {"ruta": "a.mp4", "salidas": 9})

    entrada = referencia["videos"][0]
    assert entrada["lineas"] == [{"name": "puerta"}]
    assert entrada["entradas"] == 10 and entrada["salidas"] == 9
    assert entrada["notas"] == "cámara alta"


# añadir al final de tests/analytics/test_precision.py
import pytest

from analytics.precision import (MARCA_FIN, MARCA_INICIO, cuerpo_para_el_documento,
                                 insertar_entre_marcas)


def test_insertar_reemplaza_solo_lo_que_hay_entre_las_marcas():
    doc = f"antes\n{MARCA_INICIO}\nviejo\n{MARCA_FIN}\ndespués\n"
    nuevo = insertar_entre_marcas(doc, "nuevo")

    assert "viejo" not in nuevo
    assert "nuevo" in nuevo
    assert nuevo.startswith("antes\n") and nuevo.endswith("después\n")


def test_insertar_dos_veces_no_acumula():
    doc = f"{MARCA_INICIO}\n{MARCA_FIN}\n"
    assert insertar_entre_marcas(insertar_entre_marcas(doc, "A"), "B").count("A") == 0


def test_sin_marcas_falla_en_vez_de_escribir_en_cualquier_parte():
    with pytest.raises(ValueError, match="marcas"):
        insertar_entre_marcas("# Documento sin marcas\n", "reporte")


def test_cuerpo_para_el_documento_baja_los_titulos_y_quita_el_h1():
    reporte = "# Reporte de precisión\n\ntexto\n\n## Dónde falla\n\n- nada\n"
    cuerpo = cuerpo_para_el_documento(reporte)

    assert not cuerpo.startswith("#")            # el H1 del reporte no va dentro de §4
    assert "### Dónde falla" in cuerpo
    assert "## Dónde falla" not in cuerpo.replace("### Dónde falla", "")


def test_el_documento_tecnico_tiene_las_marcas():
    from pathlib import Path

    from django.conf import settings

    doc = (Path(settings.BASE_DIR) / "docs" / "tecnico.md").read_text(encoding="utf-8")
    assert MARCA_INICIO in doc and MARCA_FIN in doc
    assert doc.index(MARCA_INICIO) < doc.index(MARCA_FIN)
