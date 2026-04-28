from decimal import Decimal

from django.db import models

from apps.materials.models import Material


class EstoqueMaterial(models.Model):
    material = models.OneToOneField(
        Material,
        on_delete=models.PROTECT,
        related_name="estoque",
    )
    saldo_fisico = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))
    saldo_reservado = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Estoque por Material"
        verbose_name_plural = "Estoques por Material"
        ordering = ["material__codigo_completo"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(saldo_fisico__gte=0),
                name="stock_estoquematerial_saldo_fisico_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(saldo_reservado__gte=0),
                name="stock_estoquematerial_saldo_reservado_non_negative",
            ),
        ]

    def __str__(self):
        return f"{self.material.codigo_completo} — disponível: {self.saldo_disponivel}"

    @property
    def saldo_disponivel(self):
        return self.saldo_fisico - self.saldo_reservado
