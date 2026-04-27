from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("matricula_funcional", "nome_completo", "email", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff", "date_joined")
    search_fields = ("matricula_funcional", "nome_completo", "email")
    ordering = ("matricula_funcional",)

    fieldsets = (
        (None, {"fields": ("matricula_funcional", "password")}),
        ("Informações pessoais", {"fields": ("nome_completo", "email")}),
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
                "fields": ("matricula_funcional", "password1", "password2", "nome_completo"),
            },
        ),
    )
