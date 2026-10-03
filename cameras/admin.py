from django.contrib import admin

from .models import Camera, CameraHealth, CountingLine, Zone


class ZoneInline(admin.TabularInline):
    model = Zone
    extra = 1


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ("name", "business", "source", "contexto", "enabled",
                    "altura_camara_m", "angulo_grados", "lost_track_buffer")
    list_filter = ("business", "enabled", "contexto")
    inlines = [ZoneInline]
    exclude = ("credencial_cifrada",)
    readonly_fields = ("credencial_usuario",)


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "camera", "kind", "contexto_efectivo")
    list_filter = ("kind",)


@admin.register(CountingLine)
class CountingLineAdmin(admin.ModelAdmin):
    list_display = ("camera", "name", "invertir")


@admin.register(CameraHealth)
class CameraHealthAdmin(admin.ModelAdmin):
    list_display = ("camera", "ultimo_latido", "frames_leidos", "reconexiones")
