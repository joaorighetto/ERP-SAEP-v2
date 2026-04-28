from django.contrib import admin

from .models import EstoqueMaterial


@admin.register(EstoqueMaterial)
class EstoqueMaterialAdmin(admin.ModelAdmin):
    list_display = (
        "material",
        "saldo_fisico",
        "saldo_reservado",
        "saldo_disponivel",
        "updated_at",
    )
    list_select_related = ("material",)
    search_fields = ("material__codigo_completo", "material__nome")
    ordering = ("material__codigo_completo",)
    readonly_fields = (
        "material",
        "saldo_fisico",
        "saldo_reservado",
        "saldo_disponivel",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        ("Material", {"fields": ("material",)}),
        ("Saldos", {"fields": ("saldo_fisico", "saldo_reservado", "saldo_disponivel")}),
        ("Datas", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff
