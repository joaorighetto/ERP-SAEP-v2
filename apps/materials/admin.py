from django.contrib import admin

from .models import GrupoMaterial, Material, SubgrupoMaterial


@admin.register(GrupoMaterial)
class GrupoMaterialAdmin(admin.ModelAdmin):
    list_display = ("codigo_grupo", "nome", "updated_at")
    search_fields = ("codigo_grupo", "nome")
    ordering = ("codigo_grupo",)
    readonly_fields = ("codigo_grupo", "nome", "created_at", "updated_at")

    fieldsets = (
        ("Informações", {"fields": ("codigo_grupo", "nome")}),
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


@admin.register(SubgrupoMaterial)
class SubgrupoMaterialAdmin(admin.ModelAdmin):
    list_display = ("grupo", "codigo_subgrupo", "nome", "updated_at")
    list_filter = ("grupo",)
    list_select_related = ("grupo",)
    search_fields = ("codigo_subgrupo", "nome", "grupo__codigo_grupo")
    ordering = ("grupo", "codigo_subgrupo")
    readonly_fields = ("grupo", "codigo_subgrupo", "nome", "created_at", "updated_at")

    fieldsets = (
        ("Informações", {"fields": ("grupo", "codigo_subgrupo", "nome")}),
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


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("codigo_completo", "nome", "unidade_medida", "is_active", "updated_at")
    list_filter = ("is_active", "subgrupo__grupo")
    list_select_related = ("subgrupo", "subgrupo__grupo")
    search_fields = (
        "codigo_completo",
        "nome",
        "descricao",
        "subgrupo__codigo_subgrupo",
        "subgrupo__grupo__codigo_grupo",
    )
    ordering = ("codigo_completo",)
    readonly_fields = (
        "subgrupo",
        "codigo_completo",
        "nome",
        "descricao",
        "unidade_medida",
        "sequencial",
        "is_active",
        "observacoes_internas",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Informações oficiais SCPI",
            {
                "fields": (
                    "subgrupo",
                    "codigo_completo",
                    "nome",
                    "descricao",
                    "unidade_medida",
                    "sequencial",
                    "is_active",
                )
            },
        ),
        ("Observações internas", {"fields": ("observacoes_internas",)}),
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
