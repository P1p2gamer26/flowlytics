"""Tests del trazado de movimiento: una persona avanza de izquierda a derecha
y el sistema devuelve un rastro ordenado, con puntos suficientes y dentro del frame.

Sin base de datos para Trajectory (no existe aún): esto falla hasta que
el modelo se implemente.
"""
import pytest


@pytest.mark.django_db
def test_una_secuencia_izquierda_a_derecha_reconstruye_el_trayecto():
    """Una persona que se mueve de izquierda a derecha deja un rastro
    cuyos puntos están ordenados por coordenada x creciente."""
    from datetime import datetime, timezone as dt_tz
    from analytics.models import Trajectory
    from cameras.models import Camera, Zone
    from tenancy.models import Business, Profile
    from django.contrib.auth.models import User

    biz = Business.objects.create(name="Demo", kind="cafe")
    user = User.objects.create_user("demo", password="x")
    Profile.objects.create(user=user, role="owner", business=biz)
    cam = Camera.objects.create(business=biz, name="Demo", source="0")

    points = [[10 + i * 5, 50] for i in range(20)]  # izquierda -> derecha
    t = Trajectory.objects.create(
        camera=cam,
        started_at=datetime(2026, 9, 1, 10, 0, tzinfo=dt_tz.utc),
        ended_at=datetime(2026, 9, 1, 10, 0, 20, tzinfo=dt_tz.utc),
        track_id=1,
        points=points,
        duration=20.0,
    )

    stored = Trajectory.objects.get(pk=t.pk)
    assert len(stored.points) == 20
    # los puntos están ordenados por x
    xs = [p[0] for p in stored.points]
    assert xs == sorted(xs)
    # todos dentro del frame (200x200 por defecto)
    assert all(0 <= p[0] <= 200 and 0 <= p[1] <= 200 for p in stored.points)


@pytest.mark.django_db
def test_un_rastro_vacio_no_se_guarden_puntos():
    """Sin puntos el rastro no se guarda: no tiene sentido persistir una
    trayectoria sin recorrido."""
    from datetime import datetime, timezone as dt_tz
    from analytics.models import Trajectory
    from cameras.models import Camera
    from tenancy.models import Business, Profile
    from django.contrib.auth.models import User

    biz = Business.objects.create(name="Demo", kind="cafe")
    user = User.objects.create_user("demo", password="x")
    Profile.objects.create(user=user, role="owner", business=biz)
    cam = Camera.objects.create(business=biz, name="Demo", source="0")

    with pytest.raises(Exception):
        Trajectory.objects.create(
            camera=cam,
            started_at=datetime(2026, 9, 1, 10, 0, tzinfo=dt_tz.utc),
            ended_at=datetime(2026, 9, 1, 10, 0, tzinfo=dt_tz.utc),
            track_id=1,
            points=[],
            duration=0.0,
        )


@pytest.mark.django_db
def test_una_ventana_sin_rastro_no_devuelve_trayectorias():
    """Si no hay Trajectory para una cámara, la consulta devuelve vacío
    en vez de fallar."""
    from cameras.models import Camera
    from tenancy.models import Business, Profile
    from django.contrib.auth.models import User

    biz = Business.objects.create(name="Demo", kind="cafe")
    user = User.objects.create_user("demo", password="x")
    Profile.objects.create(user=user, role="owner", business=biz)
    cam = Camera.objects.create(business=biz, name="Demo", source="0")

    assert cam.trajectories.count() == 0