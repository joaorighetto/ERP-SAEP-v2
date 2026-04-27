from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    matricula_funcional = models.CharField(
        max_length=20,
        unique=True,
        help_text="Identificador único de login (matrícula funcional).",
    )
    nome_completo = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "matricula_funcional"
    REQUIRED_FIELDS = ["nome_completo"]

    objects = UserManager()

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        ordering = ["matricula_funcional"]

    def __str__(self):
        return f"{self.matricula_funcional} - {self.nome_completo}"
