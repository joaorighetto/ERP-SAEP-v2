from django.db.models import Q, QuerySet

from apps.requisitions.models import Requisicao, StatusRequisicao
from apps.users.models import PapelChoices
from apps.users.policies import (
    pode_autorizar_setor,
    pode_criar_requisicao_para,  # noqa: F401 — re-export: interface exclusiva de autorização
    pode_operar_estoque,
    pode_ver_fila_atendimento,
    setor_responsavel_chefia,
    usuario_almoxarifado,
    usuario_operacional_ativo,
)


def _queryset_requisicoes_base(*, skip_prefetch: bool = False) -> QuerySet[Requisicao]:
    queryset = Requisicao.objects.select_related(
        "criador",
        "beneficiario",
        "setor_beneficiario",
        "chefe_autorizador",
        "responsavel_atendimento",
    )
    if not skip_prefetch:
        queryset = queryset.prefetch_related(
            "itens__material",
            "eventos__usuario",
        )
    return queryset


def _draft_owner_filter(user) -> Q:
    return Q(status=StatusRequisicao.RASCUNHO, criador_id=user.pk)


def _non_draft_filter(base_filter: Q) -> Q:
    return ~Q(status=StatusRequisicao.RASCUNHO) & base_filter


def _user_non_draft_personal_filter(user) -> Q:
    return Q(criador_id=user.pk) | Q(beneficiario_id=user.pk)


def user_is_creator(user, requisicao: Requisicao) -> bool:
    return requisicao.criador_id == user.pk


def queryset_requisicoes_visiveis(
    user,
    *,
    skip_prefetch: bool = False,
) -> QuerySet[Requisicao]:
    queryset = _queryset_requisicoes_base(skip_prefetch=skip_prefetch)

    if not user.is_authenticated:
        return queryset.none()

    if user.is_superuser:
        return queryset

    if not usuario_operacional_ativo(user):
        return queryset.none()

    if usuario_almoxarifado(user):
        return queryset.filter(_draft_owner_filter(user) | ~Q(status=StatusRequisicao.RASCUNHO))

    filtro = _user_non_draft_personal_filter(user)
    if user.papel == PapelChoices.CHEFE_SETOR:
        setor_responsavel = setor_responsavel_chefia(user)
        if setor_responsavel is not None:
            filtro |= Q(setor_beneficiario=setor_responsavel)

    return queryset.filter(_draft_owner_filter(user) | _non_draft_filter(filtro)).distinct()


def queryset_requisicoes_pessoais(
    user,
    *,
    skip_prefetch: bool = False,
) -> QuerySet[Requisicao]:
    queryset = _queryset_requisicoes_base(skip_prefetch=skip_prefetch)

    if not user.is_authenticated or not user.is_active:
        return queryset.none()

    filtro = _user_non_draft_personal_filter(user)
    return queryset.filter(_draft_owner_filter(user) | _non_draft_filter(filtro)).distinct()


def queryset_fila_autorizacao(user) -> QuerySet[Requisicao]:
    if not usuario_operacional_ativo(user):
        return Requisicao.objects.none()

    if user.papel == PapelChoices.CHEFE_SETOR:
        setor_responsavel = setor_responsavel_chefia(user)
        if setor_responsavel is None:
            return Requisicao.objects.none()
        return Requisicao.objects.filter(
            setor_beneficiario=setor_responsavel,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
        )

    if user.papel == PapelChoices.CHEFE_ALMOXARIFADO:
        setor_responsavel = setor_responsavel_chefia(user)
        if setor_responsavel is None:
            return Requisicao.objects.none()
        return Requisicao.objects.filter(
            setor_beneficiario=setor_responsavel,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
        )

    return Requisicao.objects.none()


def user_is_creator_or_beneficiary(user, requisicao: Requisicao) -> bool:
    return user_is_creator(user, requisicao) or requisicao.beneficiario_id == user.pk


def pode_visualizar_requisicao(user, requisicao: Requisicao) -> bool:
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    if not usuario_operacional_ativo(user):
        return False

    if requisicao.status == StatusRequisicao.RASCUNHO:
        return user_is_creator(user, requisicao)

    if user_is_creator_or_beneficiary(user, requisicao):
        return True

    if usuario_almoxarifado(user):
        return True

    return pode_autorizar_setor(user, requisicao.setor_beneficiario)


def pode_manipular_pre_autorizacao(user, requisicao: Requisicao) -> bool:
    if not usuario_operacional_ativo(user):
        return False

    if requisicao.status == StatusRequisicao.RASCUNHO:
        return user_is_creator(user, requisicao)

    return user_is_creator_or_beneficiary(user, requisicao)


def pode_cancelar_autorizada(user, requisicao: Requisicao) -> bool:
    return pode_manipular_pre_autorizacao(user, requisicao) or pode_operar_estoque(user)


def pode_cancelar_requisicao(user, requisicao: Requisicao) -> bool:
    if requisicao.status == StatusRequisicao.AUTORIZADA:
        return pode_cancelar_autorizada(user, requisicao)
    return pode_manipular_pre_autorizacao(user, requisicao)


def pode_autorizar_requisicao(user, requisicao: Requisicao) -> bool:
    return usuario_operacional_ativo(user) and pode_autorizar_setor(
        user, requisicao.setor_beneficiario
    )


def pode_atender_requisicao(user, requisicao: Requisicao) -> bool:
    return pode_operar_estoque(user) and pode_visualizar_requisicao(user, requisicao)


def pode_retirar_requisicao(user, requisicao: Requisicao) -> bool:
    return pode_operar_estoque(user) and pode_visualizar_requisicao(user, requisicao)


def queryset_fila_atendimento(user) -> QuerySet[Requisicao]:
    if not pode_ver_fila_atendimento(user):
        return Requisicao.objects.none()

    return Requisicao.objects.filter(
        status__in=(
            StatusRequisicao.AUTORIZADA,
            StatusRequisicao.PRONTA_PARA_RETIRADA,
            StatusRequisicao.PRONTA_PARA_RETIRADA_PARCIAL,
        )
    )
