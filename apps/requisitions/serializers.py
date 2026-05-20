from decimal import Decimal

from rest_framework import serializers

from apps.requisitions.models import EventoTimeline, ItemRequisicao, Requisicao


class RequisicaoUserOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    matricula_funcional = serializers.CharField(read_only=True)
    nome_completo = serializers.CharField(read_only=True)


class RequisicaoSetorOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    nome = serializers.CharField(read_only=True)


class RequisicaoMaterialOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    codigo_completo = serializers.CharField(read_only=True)
    nome = serializers.CharField(read_only=True)
    unidade_medida = serializers.CharField(read_only=True)


class RequisicaoItemCreateInputSerializer(serializers.Serializer):
    material_id = serializers.IntegerField(min_value=1)
    quantidade_solicitada = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0.001"),
    )
    observacao = serializers.CharField(required=False, allow_blank=True, default="")


class RequisicaoCreateInputSerializer(serializers.Serializer):
    beneficiario_id = serializers.IntegerField()
    observacao = serializers.CharField(required=False, allow_blank=True, default="")
    itens = RequisicaoItemCreateInputSerializer(many=True, min_length=1)


class RequisicaoItemAuthorizeInputSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    quantidade_autorizada = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0"),
    )
    justificativa_autorizacao_parcial = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class RequisicaoAuthorizeInputSerializer(serializers.Serializer):
    itens = RequisicaoItemAuthorizeInputSerializer(many=True, min_length=1)

    def validate_itens(self, itens):
        item_ids = [item["item_id"] for item in itens]
        if len(item_ids) != len(set(item_ids)):
            raise serializers.ValidationError(
                "Não é permitido repetir item_id na mesma autorização."
            )
        return itens


class RequisicaoRefuseInputSerializer(serializers.Serializer):
    motivo_recusa = serializers.CharField(allow_blank=False)


class RequisicaoCancelInputSerializer(serializers.Serializer):
    # O requisito de motivo nao e global: so o cancelamento pos-autorizacao exige texto nao vazio.
    motivo_cancelamento = serializers.CharField(required=False, allow_blank=True, default="")


class RequisicaoItemFulfillInputSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    quantidade_entregue = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0"),
    )
    justificativa_atendimento_parcial = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class RequisicaoFulfillInputSerializer(serializers.Serializer):
    observacao_atendimento = serializers.CharField(required=False, allow_blank=True, default="")
    itens = RequisicaoItemFulfillInputSerializer(
        many=True,
        required=False,
        allow_empty=False,
    )


class RequisicaoPickupInputSerializer(serializers.Serializer):
    retirante_fisico = serializers.CharField(required=True, allow_blank=False)


class RequisicaoActionOutputSerializer(serializers.ModelSerializer):
    material = RequisicaoMaterialOutputSerializer(read_only=True)

    class Meta:
        model = ItemRequisicao
        fields = [
            "id",
            "material",
            "unidade_medida",
            "quantidade_solicitada",
            "quantidade_autorizada",
            "quantidade_entregue",
            "justificativa_autorizacao_parcial",
            "justificativa_atendimento_parcial",
            "observacao",
        ]
        read_only_fields = fields


class RequisicaoTimelineEventOutputSerializer(serializers.ModelSerializer):
    usuario = RequisicaoUserOutputSerializer(read_only=True)

    class Meta:
        model = EventoTimeline
        fields = [
            "id",
            "tipo_evento",
            "usuario",
            "data_hora",
            "observacao",
        ]
        read_only_fields = fields


class RequisicaoListOutputSerializer(serializers.ModelSerializer):
    criador = RequisicaoUserOutputSerializer(read_only=True)
    beneficiario = RequisicaoUserOutputSerializer(read_only=True)
    setor_beneficiario = RequisicaoSetorOutputSerializer(read_only=True)
    total_itens = serializers.IntegerField(read_only=True)

    class Meta:
        model = Requisicao
        fields = [
            "id",
            "numero_publico",
            "status",
            "criador",
            "beneficiario",
            "setor_beneficiario",
            "data_criacao",
            "data_envio_autorizacao",
            "data_autorizacao_ou_recusa",
            "data_finalizacao",
            "updated_at",
            "total_itens",
        ]
        read_only_fields = fields


class RequisicaoListPaginatedSerializer(serializers.Serializer):
    count = serializers.IntegerField(read_only=True)
    page = serializers.IntegerField(read_only=True)
    page_size = serializers.IntegerField(read_only=True)
    total_pages = serializers.IntegerField(read_only=True)
    next = serializers.URLField(allow_null=True, read_only=True)
    previous = serializers.URLField(allow_null=True, read_only=True)
    results = RequisicaoListOutputSerializer(many=True, read_only=True)


class RequisicaoDetailOutputSerializer(serializers.ModelSerializer):
    criador = RequisicaoUserOutputSerializer(read_only=True)
    beneficiario = RequisicaoUserOutputSerializer(read_only=True)
    setor_beneficiario = RequisicaoSetorOutputSerializer(read_only=True)
    chefe_autorizador = RequisicaoUserOutputSerializer(read_only=True)
    responsavel_atendimento = RequisicaoUserOutputSerializer(read_only=True)
    itens = RequisicaoActionOutputSerializer(many=True, read_only=True)
    eventos = RequisicaoTimelineEventOutputSerializer(many=True, read_only=True)

    class Meta:
        model = Requisicao
        fields = [
            "id",
            "numero_publico",
            "status",
            "criador",
            "beneficiario",
            "setor_beneficiario",
            "chefe_autorizador",
            "responsavel_atendimento",
            "data_criacao",
            "data_envio_autorizacao",
            "data_autorizacao_ou_recusa",
            "motivo_recusa",
            "motivo_cancelamento",
            "data_finalizacao",
            "retirante_fisico",
            "data_retirada",
            "observacao",
            "observacao_atendimento",
            "itens",
            "eventos",
        ]
        read_only_fields = fields


class RequisicaoPendingApprovalOutputSerializer(serializers.ModelSerializer):
    criador = RequisicaoUserOutputSerializer(read_only=True)
    beneficiario = RequisicaoUserOutputSerializer(read_only=True)
    setor_beneficiario = RequisicaoSetorOutputSerializer(read_only=True)
    total_itens = serializers.IntegerField(read_only=True)

    class Meta:
        model = Requisicao
        fields = [
            "id",
            "numero_publico",
            "status",
            "data_envio_autorizacao",
            "criador",
            "beneficiario",
            "setor_beneficiario",
            "total_itens",
        ]
        read_only_fields = fields


class RequisicaoPendingApprovalPaginatedSerializer(serializers.Serializer):
    count = serializers.IntegerField(read_only=True)
    page = serializers.IntegerField(read_only=True)
    page_size = serializers.IntegerField(read_only=True)
    total_pages = serializers.IntegerField(read_only=True)
    next = serializers.URLField(allow_null=True, read_only=True)
    previous = serializers.URLField(allow_null=True, read_only=True)
    results = RequisicaoPendingApprovalOutputSerializer(many=True, read_only=True)


class RequisicaoPendingFulfillmentOutputSerializer(serializers.ModelSerializer):
    beneficiario = RequisicaoUserOutputSerializer(read_only=True)
    setor_beneficiario = RequisicaoSetorOutputSerializer(read_only=True)
    chefe_autorizador = RequisicaoUserOutputSerializer(read_only=True)
    total_itens = serializers.IntegerField(read_only=True)

    class Meta:
        model = Requisicao
        fields = [
            "id",
            "numero_publico",
            "status",
            "beneficiario",
            "setor_beneficiario",
            "chefe_autorizador",
            "data_autorizacao_ou_recusa",
            "total_itens",
        ]
        read_only_fields = fields


class RequisicaoPendingFulfillmentPaginatedSerializer(serializers.Serializer):
    count = serializers.IntegerField(read_only=True)
    page = serializers.IntegerField(read_only=True)
    page_size = serializers.IntegerField(read_only=True)
    total_pages = serializers.IntegerField(read_only=True)
    next = serializers.URLField(allow_null=True, read_only=True)
    previous = serializers.URLField(allow_null=True, read_only=True)
    results = RequisicaoPendingFulfillmentOutputSerializer(many=True, read_only=True)
