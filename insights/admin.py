from django.contrib import admin

from .models import CorpusEntry, Insight


@admin.register(Insight)
class InsightAdmin(admin.ModelAdmin):
    list_display = ("business", "day", "model", "created_at")
    list_filter = ("business", "model")


@admin.register(CorpusEntry)
class CorpusEntryAdmin(admin.ModelAdmin):
    list_display = ("cohorte", "day", "visitantes", "aforo_pico", "espera_fila_seg")
    list_filter = ("cohorte",)
    date_hierarchy = "day"
