from django.urls import path

from .views import app_shell, sistema

urlpatterns = [
    path("", app_shell, name="home"),
    path("sistema/", sistema, name="sistema"),
    path("<path:resto>", app_shell, name="app"),
]
