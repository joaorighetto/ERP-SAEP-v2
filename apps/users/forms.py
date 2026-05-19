from django import forms
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


class LoginForm(forms.Form):
    """Formulário de login HTML server-rendered. Autenticação ocorre na view."""

    matricula_funcional = forms.CharField(
        label="Matrícula funcional",
        max_length=20,
        widget=forms.TextInput(attrs={"autocomplete": "username", "autofocus": True}),
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
