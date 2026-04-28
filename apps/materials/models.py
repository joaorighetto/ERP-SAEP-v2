from django.core.validators import RegexValidator
from django.db import models

codigo_scpi_validator = RegexValidator(
    regex=r"^\d{3}$",
    message="O código SCPI deve conter exatamente 3 dígitos numéricos.",
)

codigo_completo_validator = RegexValidator(
    regex=r"^\d{3}\.\d{3}\.\d{3}$",
    message="O código completo deve seguir o padrão xxx.yyy.zzz.",
)


class GrupoMaterial(models.Model):
    codigo_grupo = models.CharField(
        max_length=3,
        unique=True,
        validators=[codigo_scpi_validator],
        help_text="Código xxx do grupo no SCPI",
    )
    nome = models.CharField(max_length=200, help_text="Nome descritivo vindo do SCPI")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Grupo de Material"
        verbose_name_plural = "Grupos de Material"
        ordering = ["codigo_grupo"]

    def __str__(self):
        return f"{self.codigo_grupo} — {self.nome}"


class SubgrupoMaterial(models.Model):
    grupo = models.ForeignKey(
        GrupoMaterial,
        on_delete=models.PROTECT,
        related_name="subgrupos",
        help_text="Grupo de material pai",
    )
    codigo_subgrupo = models.CharField(
        max_length=3,
        validators=[codigo_scpi_validator],
        help_text="Código yyy do subgrupo no SCPI",
    )
    nome = models.CharField(max_length=200, help_text="Nome descritivo vindo do SCPI")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Subgrupo de Material"
        verbose_name_plural = "Subgrupos de Material"
        ordering = ["grupo", "codigo_subgrupo"]
        constraints = [
            models.UniqueConstraint(
                fields=["grupo", "codigo_subgrupo"], name="unique_subgrupo_por_grupo"
            )
        ]

    def __str__(self):
        return f"{self.grupo.codigo_grupo}.{self.codigo_subgrupo} — {self.nome}"


class Material(models.Model):
    subgrupo = models.ForeignKey(
        SubgrupoMaterial,
        on_delete=models.PROTECT,
        related_name="materiais",
        help_text="Subgrupo do material no SCPI",
    )
    codigo_completo = models.CharField(
        max_length=11,
        unique=True,
        validators=[codigo_completo_validator],
        help_text="Código completo no formato xxx.yyy.zzz",
    )
    nome = models.CharField(max_length=255, help_text="Nome oficial vindo do SCPI")
    descricao = models.TextField(blank=True, help_text="Descrição oficial vinda do SCPI")
    unidade_medida = models.CharField(
        max_length=20,
        help_text="Unidade de medida oficial do SCPI",
    )
    sequencial = models.CharField(
        max_length=3,
        validators=[codigo_scpi_validator],
        help_text="Sequencial zzz do código SCPI",
    )
    is_active = models.BooleanField(default=True)
    observacoes_internas = models.TextField(
        blank=True,
        help_text="Campo interno do ERP-SAEP, não sincronizado com SCPI",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Material"
        verbose_name_plural = "Materiais"
        ordering = ["codigo_completo"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(codigo_completo__regex=r"^\d{3}\.\d{3}\.\d{3}$"),
                name="materials_material_codigo_completo_format",
            )
        ]

    def __str__(self):
        return f"{self.codigo_completo} — {self.nome}"
