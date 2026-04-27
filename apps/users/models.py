from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .managers import UserManager


class Setor(models.Model):
    nome = models.CharField(
        max_length=200,
        unique=True,
        help_text="Nome do setor organizacional.",
    )
    chefe_responsavel = models.OneToOneField(
        "User",
        on_delete=models.PROTECT,
        related_name="setor_responsavel",
        help_text="Chefe responsável pelo setor.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Setores inativos permanecem em históricos mas não recebem novas requisições.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Setor"
        verbose_name_plural = "Setores"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} (Chefe: {self.chefe_responsavel.matricula_funcional})"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError

        if not self.chefe_responsavel_id:
            raise ValidationError(
                {"chefe_responsavel": "Todo setor deve ter um chefe responsável."}
            )


class User(AbstractBaseUser, PermissionsMixin):
    matricula_funcional = models.CharField(
        max_length=20,
        unique=True,
        help_text="Identificador único de login (matrícula funcional).",
    )
    nome_completo = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    setor = models.ForeignKey(
        "Setor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="usuarios",
        db_index=True,
        help_text="Setor ao qual o usuário pertence.",
    )
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
