"""La función que corre YOLO sobre un video real no se prueba aquí (necesita
el modelo y el archivo real): se prueba la que arma el informe a partir de un
diagnóstico ya calculado, igual que reporte_precision separa `medir_video` de
`generar_reporte`."""
from vision.management.commands.diagnostico_cajas import informe_de_diagnostico

def test_el_informe_dice_si_hace_falta_reescalar():
    diagnostico = {"necesita_reescalar": True, "cajas_fuera_de_referencia": 3,
                  "salto_maximo_por_track": {1: 12.5, 2: 480.0}}

    texto = informe_de_diagnostico("mi_video.mp4", diagnostico, umbral_salto=200)

    assert "necesita reescalarse" in texto
    assert "3 caja" in texto
    assert "track 2" in texto  # el salto de 480 supera el umbral, se cita
    assert "track 1" not in texto  # el de 12.5 no es sospechoso, no se cita

def test_el_informe_dice_que_todo_esta_bien_si_nada_sospechoso():
    diagnostico = {"necesita_reescalar": False, "cajas_fuera_de_referencia": 0,
                  "salto_maximo_por_track": {1: 8.0}}

    texto = informe_de_diagnostico("mi_video.mp4", diagnostico, umbral_salto=200)

    assert "no necesita reescalarse" in texto
    assert "ninguna caja" in texto