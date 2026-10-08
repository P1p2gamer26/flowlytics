"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from analytics.api import (events_view, negocio_actual_view, panel_extra_view, summary_view,
                           avisos_view, aviso_detalle_view, aviso_horario_view, simular_aviso_view)
from analytics.reportes_views import reporte_csv, reporte_pdf
from cameras.api import (
    camara_ahora_view,
    camara_describir_view,
    camara_detalle_view,
    camara_estelas_view,
    camaras_en_vivo_view,
    camaras_grid_view,
    camara_mapa_calor_view,
    camara_procesar_view,
    camara_progreso_view,
    camara_sugerir_zona_view,
    camara_trayectorias_view,
    camara_video_view,
    camara_personal_view,
    camara_recorrido_view,
    camara_vista_view,
    camaras_view,
    linea_detalle_view,
    lineas_view,
    probar_camara_view,
    subir_video_view,
    zona_detalle_view,
    zonas_view,
)
from dashboard.views import salud

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/summary/", summary_view),
    path("api/events/", events_view),
    path("api/negocio-actual/", negocio_actual_view),
    path("api/panel-extra/", panel_extra_view),
    path("api/avisos/", avisos_view),
    path("api/avisos/horario/", aviso_horario_view),
    path("api/avisos/simular/", simular_aviso_view),
    path("api/avisos/<int:regla_id>/", aviso_detalle_view),
    path("api/camaras/", camaras_view),
    path("api/camaras/en_vivo/", camaras_en_vivo_view),
    path("api/camaras/grid/", camaras_grid_view),
    path("api/camaras/probar/", probar_camara_view),
    path("api/camaras/subir/", subir_video_view),
    path("api/camaras/<int:camera_id>/", camara_detalle_view),
    path("api/camaras/<int:camera_id>/vista/", camara_vista_view),
    path("api/camaras/<int:camera_id>/recorrido/", camara_recorrido_view),
    path("api/camaras/<int:camera_id>/mapa_calor/", camara_mapa_calor_view),
    path("api/camaras/<int:camera_id>/personal/", camara_personal_view),
    path("api/camaras/<int:camera_id>/video/", camara_video_view),
    path("api/camaras/<int:camera_id>/sugerir_zona/", camara_sugerir_zona_view),
    path("api/camaras/<int:camera_id>/describir/", camara_describir_view),
    path("api/camaras/<int:camera_id>/procesar/", camara_procesar_view),
    path("api/camaras/<int:camera_id>/progreso/", camara_progreso_view),
    path("api/camaras/<int:camera_id>/trayectorias/", camara_trayectorias_view),
    path("api/camaras/<int:camera_id>/estelas/", camara_estelas_view),
    path("api/camaras/<int:camera_id>/zonas/", zonas_view),
    path("api/camaras/<int:camera_id>/lineas/", lineas_view),
    path("api/camaras/<int:camera_id>/ahora/", camara_ahora_view),
    path("api/zonas/<int:zona_id>/", zona_detalle_view),
    path("api/lineas/<int:linea_id>/", linea_detalle_view),
]

urlpatterns += [
    path("accounts/", include("django.contrib.auth.urls")),
    path("salud/", salud),
    path("reporte/csv/", reporte_csv, name="reporte_csv"),
    path("reporte/pdf/", reporte_pdf, name="reporte_pdf"),
    path("", include("tenancy.urls")),
    path("", include("dashboard.urls")),
]
