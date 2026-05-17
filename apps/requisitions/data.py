from rest_framework.exceptions import NotFound

from apps.requisitions.models import ItemRequisicao, Requisicao
from apps.users.models import Setor, User

# --- Recarregar (leitura pós-transação) ---


def recarregar_rascunho(pk: int) -> Requisicao:
    return (
        Requisicao.objects.select_related("criador", "beneficiario", "setor_beneficiario")
        .prefetch_related("itens__material", "eventos__usuario")
        .get(pk=pk)
    )


def recarregar_autorizado(pk: int) -> Requisicao:
    return (
        Requisicao.objects.select_related(
            "criador", "beneficiario", "setor_beneficiario", "chefe_autorizador"
        )
        .prefetch_related("itens__material__estoque", "eventos__usuario")
        .get(pk=pk)
    )


def recarregar_atendido(pk: int) -> Requisicao:
    return (
        Requisicao.objects.select_related(
            "criador",
            "beneficiario",
            "setor_beneficiario",
            "chefe_autorizador",
            "responsavel_atendimento",
        )
        .prefetch_related("itens__material__estoque", "eventos__usuario")
        .get(pk=pk)
    )


def recarregar_detalhe(requisicao_id: int) -> Requisicao:
    return (
        Requisicao.objects.select_related(
            "criador",
            "beneficiario",
            "setor_beneficiario",
            "chefe_autorizador",
            "responsavel_atendimento",
        )
        .prefetch_related("itens__material__estoque", "eventos__usuario")
        .get(pk=requisicao_id)
    )


# --- Carregar com lock (dentro de transação) ---


def recarregar_para_autorizacao(requisicao: Requisicao) -> Requisicao:
    return (
        Requisicao.objects.select_for_update(of=("self",))
        .select_related("criador", "beneficiario", "setor_beneficiario")
        .prefetch_related("itens__material__estoque", "eventos__usuario")
        .get(pk=requisicao.pk)
    )


def recarregar_para_atendimento(requisicao: Requisicao) -> Requisicao:
    return (
        Requisicao.objects.select_for_update(of=("self",))
        .select_related("criador", "beneficiario", "setor_beneficiario")
        .prefetch_related("itens__material__estoque", "eventos__usuario")
        .get(pk=requisicao.pk)
    )


def carregar_rascunho_bloqueado(requisicao_id: int) -> Requisicao:
    try:
        return (
            Requisicao.objects.select_related("criador", "beneficiario", "setor_beneficiario")
            .select_for_update(of=("self",))
            .prefetch_related("itens__material", "eventos__usuario")
            .get(pk=requisicao_id)
        )
    except Requisicao.DoesNotExist as exc:
        raise NotFound("Requisição não encontrada.") from exc


def carregar_beneficiario_e_setor(beneficiario_id: int) -> tuple[User, Setor]:
    try:
        beneficiario = User.objects.select_for_update().get(pk=beneficiario_id)
    except User.DoesNotExist as exc:
        raise NotFound("Beneficiário não encontrado.") from exc
    if not beneficiario.setor_id:
        raise NotFound("Beneficiário deve possuir setor válido.")
    try:
        setor = Setor.objects.select_for_update().get(pk=beneficiario.setor_id)
    except Setor.DoesNotExist as exc:
        raise NotFound("Setor do beneficiário não encontrado.") from exc
    return beneficiario, setor


def carregar_itens_bloqueados(requisicao: Requisicao) -> list[ItemRequisicao]:
    return list(
        ItemRequisicao.objects.select_for_update(of=("self",))
        .select_related("material")
        .filter(requisicao=requisicao)
        .order_by("material_id", "id")
    )


# --- Escrever (dentro de transação) ---


def bulk_create_itens(requisicao: Requisicao, itens, materiais) -> None:
    materiais_por_id = {m.pk: m for m in materiais}
    ItemRequisicao.objects.bulk_create(
        [
            ItemRequisicao(
                requisicao=requisicao,
                material=materiais_por_id[item.material_id],
                unidade_medida=materiais_por_id[item.material_id].unidade_medida,
                quantidade_solicitada=item.quantidade_solicitada,
                observacao=item.observacao,
            )
            for item in itens
        ]
    )


def aplicar_edicao_rascunho(requisicao, beneficiario, setor, observacao, itens, materiais) -> None:
    requisicao.beneficiario = beneficiario
    requisicao.setor_beneficiario = setor
    requisicao.observacao = observacao
    requisicao.full_clean()
    requisicao.save(
        update_fields=["beneficiario", "setor_beneficiario", "observacao", "updated_at"]
    )
    requisicao.itens.all().delete()
    bulk_create_itens(requisicao, itens, materiais)


def aplicar_quantidades_autorizacao(itens_requisicao, itens_por_id) -> None:
    for item_req in itens_requisicao:
        item_aut = itens_por_id[item_req.id]
        item_req.quantidade_autorizada = item_aut.quantidade_autorizada
        item_req.justificativa_autorizacao_parcial = item_aut.justificativa_autorizacao_parcial
        item_req.full_clean()
        item_req.save(
            update_fields=[
                "quantidade_autorizada",
                "justificativa_autorizacao_parcial",
                "updated_at",
            ]
        )


def aplicar_itens_atendimento_completo(itens_autorizados) -> None:
    for item in itens_autorizados:
        item.quantidade_entregue = item.quantidade_autorizada
        item.justificativa_atendimento_parcial = ""
        item.full_clean()
        item.save(
            update_fields=["quantidade_entregue", "justificativa_atendimento_parcial", "updated_at"]
        )


def aplicar_itens_atendimento_parcial(itens_autorizados, dados_por_item_id) -> None:
    for item in itens_autorizados:
        item_data = dados_por_item_id[item.id]
        quantidade_nao_entregue = item.quantidade_autorizada - item_data.quantidade_entregue
        item.quantidade_entregue = item_data.quantidade_entregue
        item.justificativa_atendimento_parcial = (
            item_data.justificativa_atendimento_parcial.strip()
            if quantidade_nao_entregue > 0
            else ""
        )
        item.full_clean()
        item.save(
            update_fields=["quantidade_entregue", "justificativa_atendimento_parcial", "updated_at"]
        )
