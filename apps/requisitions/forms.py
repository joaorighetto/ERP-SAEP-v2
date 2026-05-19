"""Forms de requisição para o frontend server-rendered.

Estes forms são usados apenas pelas views HTML em apps/web.
Validação de domínio (saldo, permissão, estado) ocorre no service, não aqui.
"""

from decimal import Decimal

from django import forms
from django.forms import formset_factory


class ItemRequisicaoForm(forms.Form):
    """Linha de item em rascunho de requisição."""

    material_id = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=False,
    )
    quantidade_solicitada = forms.DecimalField(
        label="Quantidade",
        min_value=Decimal("0.001"),
        decimal_places=3,
        max_digits=12,
        widget=forms.NumberInput(
            attrs={
                "step": "0.001",
                "min": "0.001",
                "placeholder": "0",
                "autocomplete": "off",
            }
        ),
        required=False,
    )
    observacao = forms.CharField(
        label="Observação do item",
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Opcional"}),
    )

    def clean(self):
        cleaned = super().clean()
        # Linha marcada para DELETE: ignorar validações de conteúdo.
        if self.cleaned_data.get("DELETE"):
            return cleaned

        material_id = cleaned.get("material_id")
        quantidade = cleaned.get("quantidade_solicitada")

        # Linha completamente vazia → ignorada (sem erro).
        if not material_id and not quantidade:
            return cleaned

        if not material_id:
            self.add_error("material_id", "Selecione o material.")
        if not quantidade:
            self.add_error("quantidade_solicitada", "Informe a quantidade.")

        return cleaned


# Formset com can_delete=True para suportar remoção de linhas via Alpine.js.
ItemRequisicaoFormSet = formset_factory(
    ItemRequisicaoForm,
    extra=0,
    can_delete=True,
    min_num=1,
    validate_min=False,  # Validação mínima feita na view ao processar itens ativos.
)


class RequisicaoRascunhoForm(forms.Form):
    """Cabeçalho de rascunho: beneficiário e observação geral."""

    beneficiario_id = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=True,
        error_messages={"required": "Selecione o beneficiário."},
    )
    observacao = forms.CharField(
        label="Observação geral",
        max_length=1000,
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Opcional"}),
    )
