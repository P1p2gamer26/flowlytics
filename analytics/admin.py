from django.contrib import admin

from .models import (AlertDelivery, AlertRule, CrossingWindow, Event, EventClip,
                    JobRun, MetricWindow)


@admin.register(MetricWindow)
class MetricWindowAdmin(admin.ModelAdmin):
    list_display = ("camera", "zone_name", "started_at", "occupancy_avg",
                    "occupancy_max", "dwell_seconds")
    list_filter = ("camera__business", "zone_kind")
    date_hierarchy = "started_at"


@admin.register(CrossingWindow)
class CrossingWindowAdmin(admin.ModelAdmin):
    list_display = ("camera", "line_name", "started_at", "entradas", "salidas")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("camera", "kind", "zone_name", "value", "occurred_at")
    list_filter = ("kind", "camera__business")


@admin.register(EventClip)
class EventClipAdmin(admin.ModelAdmin):
    list_display = ("event", "file", "expires_at")


@admin.register(JobRun)
class JobRunAdmin(admin.ModelAdmin):
    list_display = ("nombre", "terminado_en", "ok")


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ("business", "tipo_evento", "canal", "activa", "ultima_notificacion")
    list_filter = ("tipo_evento", "canal", "activa")


@admin.register(AlertDelivery)
class AlertDeliveryAdmin(admin.ModelAdmin):
    list_display = ("rule", "resultado", "creado")
    list_filter = ("resultado",)
