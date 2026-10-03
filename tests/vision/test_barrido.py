from vision.management.commands.barrido_deteccion import aguanta_en_vivo, tabla


def test_dice_si_la_cpu_aguanta_ese_muestreo():
    assert aguanta_en_vivo(segundos_por_frame=0.2, fps=2) is True
    assert aguanta_en_vivo(segundos_por_frame=0.2, fps=6) is False


def test_la_tabla_ordena_por_personas_y_marca_lo_que_no_aguanta():
    filas = [
        {"imgsz": 416, "fps": 2, "personas_por_frame": 1.1,
         "segundos_por_frame": 0.20, "aguanta_en_vivo": True},
        {"imgsz": 640, "fps": 6, "personas_por_frame": 2.4,
         "segundos_por_frame": 0.45, "aguanta_en_vivo": False},
    ]
    texto = tabla(filas)
    assert "640" in texto and "2.4" in texto
    assert "no aguanta" in texto.lower()
