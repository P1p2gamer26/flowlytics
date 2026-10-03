import pytest

from analytics.models import HeatmapWindow


@pytest.mark.django_db
def test_from_grid_guarda_las_dimensiones_y_la_rejilla(camara_demo):
    HeatmapWindow.from_grid(camara_demo, started_epoch=0.0, ended_epoch=60.0,
                            grid=[[1, 2], [3, 4]], personas=5)
    v = HeatmapWindow.objects.get(camera=camara_demo)
    assert v.grid_rows == 2 and v.grid_cols == 2
    assert v.counts == [[1, 2], [3, 4]]
    assert v.personas == 5
    assert v.started_at < v.ended_at


@pytest.mark.django_db
def test_una_camara_tiene_muchas_ventanas_de_calor(camara_demo):
    """A diferencia de Recorrido (una fila por cámara), aquí cada ventana se
    conserva: es lo que permite comparar un día contra otro."""
    HeatmapWindow.from_grid(camara_demo, started_epoch=0.0, ended_epoch=60.0,
                            grid=[[1]], personas=1)
    HeatmapWindow.from_grid(camara_demo, started_epoch=60.0, ended_epoch=120.0,
                            grid=[[2]], personas=2)
    assert HeatmapWindow.objects.filter(camera=camara_demo).count() == 2
