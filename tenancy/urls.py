from django.urls import path

from . import views

urlpatterns = [
    path("registro/", views.registrar, name="registro"),
    path("onboarding/", views.onboarding, name="onboarding"),
    path("invitar/", views.invitar, name="invitar"),
    path("invitacion/<str:token>/", views.aceptar_invitacion, name="aceptar_invitacion"),
    path("plataforma/", views.plataforma, name="plataforma"),
]
