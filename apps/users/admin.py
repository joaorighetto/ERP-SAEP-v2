from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Setor, User


@admin.register(Setor)
class SetorAdmin(admin.ModelAdmin):
    list_display = ("nome", "chefe_responsavel", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = (
        "nome",
        "chefe_responsavel__matricula_funcional",
        "chefe_responsavel__nome_completo",
    )
    ordering = ("nome",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("nome", "chefe_responsavel", "is_active")}),
        ("Datas", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "matricula_funcional",
        "nome_completo",
        "setor",
        "email",
        "is_active",
        "is_staff",
    )
    list_filter = ("is_active", "is_staff", "setor", "date_joined")
    search_fields = ("matricula_funcional", "nome_completo", "email")
    ordering = ("matricula_funcional",)

    fieldsets = (
        (None, {"fields": ("matricula_funcional", "password")}),
        ("Informações pessoais", {"fields": ("nome_completo", "email", "setor")}),
        (
            "Permissões",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Datas importantes", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "matricula_funcional",
                    "password1",
                    "password2",
                    "nome_completo",
                    "setor",
                ),
            },
        ),
    )
