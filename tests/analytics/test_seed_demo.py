import pytest
from django.contrib.auth.models import User
from django.core.management import call_command

from analytics.models import CrossingWindow, MetricWindow
from cameras.models import Camera
from tenancy.models import Business, Profile


@pytest.mark.django_db
def test_seed_demo_crea_negocio_usuario_y_metricas():
    call_command("seed_demo", "--dias", "3")

    biz = Business.objects.get(name="Demo")
    assert Profile.objects.filter(business=biz, role="owner").exists()
    assert User.objects.filter(username="demo").exists()
    assert Camera.objects.filter(business=biz).exists()
    assert MetricWindow.objects.filter(camera__business=biz).exists()
    assert CrossingWindow.objects.filter(camera__business=biz).exists()


@pytest.mark.django_db
def test_seed_demo_es_idempotente():
    call_command("seed_demo", "--dias", "3")
    n1 = MetricWindow.objects.count()
    negocios1 = Business.objects.filter(name="Demo").count()

    call_command("seed_demo", "--dias", "3")
    assert MetricWindow.objects.count() == n1          # no duplicó métricas
    assert Business.objects.filter(name="Demo").count() == negocios1 == 1


@pytest.mark.django_db
def test_seed_demo_no_usa_la_webcam():
    from cameras.models import Camera
    call_command("seed_demo", "--dias", "1")
    cam = Camera.objects.get(name="Cámara demo")
    assert cam.source != "0"
    cam.source = "0"
    cam.save()
    call_command("seed_demo", "--dias", "1")
    cam.refresh_from_db()
    assert cam.source != "0"
