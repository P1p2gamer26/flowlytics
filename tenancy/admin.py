from django.contrib import admin

from .models import AuditLog, Business, Invitation, Plan, Profile


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "plan", "timezone", "comparte_corpus", "created_at")
    list_filter = ("kind",)
    search_fields = ("name",)


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("nombre", "max_camaras", "retencion_dias", "precio_centavos")


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("business", "email", "role", "aceptada", "creado")
    list_filter = ("aceptada", "role")
    readonly_fields = ("token",)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "business")
    list_filter = ("role",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("creado", "usuario", "accion", "objeto", "ip")
    readonly_fields = ("usuario", "accion", "objeto", "ip", "creado")

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False
