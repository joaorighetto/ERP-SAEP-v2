from django.contrib.auth.forms import UserChangeForm as DjangoUserChangeForm
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm

from .models import User


class UserCreationForm(DjangoUserCreationForm):
    class Meta:
        model = User
        fields = ("matricula_funcional", "nome_completo", "email")


class UserChangeForm(DjangoUserChangeForm):
    class Meta:
        model = User
        fields = (
            "matricula_funcional",
            "nome_completo",
            "email",
            "is_active",
            "is_staff",
            "groups",
            "user_permissions",
        )
