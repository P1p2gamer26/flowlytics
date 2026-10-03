import pytest

from cameras.procesamiento import lanzar, progreso


@pytest.mark.django_db
def test_lanzar_arma_el_comando_de_una_pasada(camara_demo):
    comandos = []
    lanzar(camara_demo, segundos=30, ejecutar=comandos.append)
    (cmd,) = comandos
    assert "run_camera" in cmd
    assert str(camara_demo.pk) in cmd
    assert "--una-pasada" in cmd
    assert "--max-seconds" in cmd and "30" in cmd


@pytest.mark.django_db
def test_lanzar_sin_zonas_avisa_en_vez_de_arrancar(camara_demo):
    camara_demo.zones.all().delete()
    with pytest.raises(ValueError, match="zona"):
        lanzar(camara_demo, segundos=None, ejecutar=lambda cmd: None)


@pytest.mark.django_db
def test_progreso_cuenta_ventanas_y_eventos(camara_demo, ventana_demo):
    datos = progreso(camara_demo)
    assert datos["ventanas"] == 1
    assert datos["eventos"] == 0
    assert datos["viva"] is False


@pytest.mark.django_db
def test_progreso_cuenta_las_reconexiones_y_el_ultimo_motivo(camara_demo):
    from cameras.models import CameraHealth

    CameraHealth.latir(camara_demo, frames=10, reconexiones=3,
                       error="sin señal: la fuente dejó de entregar imagen")

    datos = progreso(camara_demo)

    assert datos["reconexiones"] == 3
    assert "sin señal" in datos["ultimo_error"]
