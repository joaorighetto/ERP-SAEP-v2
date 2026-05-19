from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.requisitions.models import Requisicao, StatusRequisicao
from apps.requisitions.policies import (
    pode_atender_requisicao,
    pode_autorizar_requisicao,
    pode_cancelar_requisicao,
    pode_manipular_pre_autorizacao,
    pode_visualizar_requisicao,
)

User = get_user_model()


def _recarregar_com_lock(pk: int) -> Requisicao:
    try:
        return (
            Requisicao.objects.select_for_update(of=("self",))
            .select_related("criador", "beneficiario", "setor_beneficiario")
            .prefetch_related("itens__material__estoque", "eventos__usuario")
            .get(pk=pk)
        )
    except Requisicao.DoesNotExist as exc:
        raise NotFound("Requisição não encontrada.") from exc


@dataclass
class ContextoEnvio:
    requisicao: Requisicao
    ator: User
    is_primeiro_envio: bool = field(default=False)

    @classmethod
    @contextmanager
    def abrir(cls, requisicao: Requisicao, ator: User) -> Generator[ContextoEnvio]:
        with transaction.atomic():
            req = _recarregar_com_lock(requisicao.pk)
            if not pode_visualizar_requisicao(ator, req):
                raise NotFound("Requisição não encontrada.")
            if not pode_manipular_pre_autorizacao(ator, req):
                raise PermissionDenied("Apenas criador pode enviar a requisição.")
            yield cls(
                requisicao=req,
                ator=ator,
                is_primeiro_envio=not req.numero_publico,
            )


@dataclass
class ContextoAutorizacao:
    requisicao: Requisicao
    ator: User

    @classmethod
    @contextmanager
    def abrir(cls, requisicao: Requisicao, ator: User) -> Generator[ContextoAutorizacao]:
        with transaction.atomic():
            req = _recarregar_com_lock(requisicao.pk)
            if not pode_visualizar_requisicao(ator, req):
                raise NotFound("Requisição não encontrada.")
            if not pode_autorizar_requisicao(ator, req):
                raise PermissionDenied("Usuário sem permissão para autorizar esta requisição.")
            yield cls(requisicao=req, ator=ator)


@dataclass
class ContextoCancelamento:
    requisicao: Requisicao
    ator: User
    requer_liberacao_estoque: bool = field(default=False)

    @classmethod
    @contextmanager
    def abrir(cls, requisicao: Requisicao, ator: User) -> Generator[ContextoCancelamento]:
        with transaction.atomic():
            req = _recarregar_com_lock(requisicao.pk)
            if not pode_visualizar_requisicao(ator, req):
                raise NotFound("Requisição não encontrada.")
            if not pode_cancelar_requisicao(ator, req):
                raise PermissionDenied("Usuário sem permissão para cancelar esta requisição.")
            yield cls(
                requisicao=req,
                ator=ator,
                requer_liberacao_estoque=req.status == StatusRequisicao.AUTORIZADA,
            )


@dataclass
class ContextoAtendimento:
    requisicao: Requisicao
    ator: User

    @classmethod
    @contextmanager
    def abrir(cls, requisicao: Requisicao, ator: User) -> Generator[ContextoAtendimento]:
        with transaction.atomic():
            req = _recarregar_com_lock(requisicao.pk)
            if not pode_visualizar_requisicao(ator, req):
                raise NotFound("Requisição não encontrada.")
            if not pode_atender_requisicao(ator, req):
                raise PermissionDenied("Usuário sem permissão para atender esta requisição.")
            yield cls(requisicao=req, ator=ator)


# ---------------------------------------------------------------------------
# Worklist presenter — Minhas solicitações
# ---------------------------------------------------------------------------

_STATUS_VARIANT: dict[str, str] = {
    StatusRequisicao.RASCUNHO: "neutral",
    StatusRequisicao.AGUARDANDO_AUTORIZACAO: "info",
    StatusRequisicao.RECUSADA: "danger",
    StatusRequisicao.AUTORIZADA: "success",
    StatusRequisicao.PRONTA_PARA_RETIRADA_PARCIAL: "warning",
    StatusRequisicao.PRONTA_PARA_RETIRADA: "success",
    StatusRequisicao.RETIRADA: "neutral",
    StatusRequisicao.CANCELADA: "danger",
    StatusRequisicao.ESTORNADA: "danger",
}


def _data_label(req: Requisicao) -> str:
    if req.status == StatusRequisicao.RASCUNHO:
        return f"Criado em {req.created_at.strftime('%d/%m/%Y')}"
    if req.status in (
        StatusRequisicao.RETIRADA,
        StatusRequisicao.PRONTA_PARA_RETIRADA,
        StatusRequisicao.PRONTA_PARA_RETIRADA_PARCIAL,
    ):
        if req.data_finalizacao:
            return f"Finalizado em {req.data_finalizacao.strftime('%d/%m/%Y')}"
    if req.data_autorizacao_ou_recusa:
        if req.status == StatusRequisicao.RECUSADA:
            return f"Recusado em {req.data_autorizacao_ou_recusa.strftime('%d/%m/%Y')}"
        return f"Autorizado em {req.data_autorizacao_ou_recusa.strftime('%d/%m/%Y')}"
    if req.data_envio_autorizacao:
        return f"Enviado em {req.data_envio_autorizacao.strftime('%d/%m/%Y')}"
    return f"Atualizado em {req.updated_at.strftime('%d/%m/%Y')}"


@dataclass
class RequisicaoWorklistItem:
    id: int
    detail_url: str | None
    is_rascunho: bool
    numero_publico: str | None
    status_value: str
    status_label: str
    status_variant: str
    data_label: str
    is_beneficiario_terceiro: bool
    beneficiario_nome: str | None
    resumo_itens: str
    can_view_detail: bool


def build_requisicao_worklist_item(req: Requisicao, user) -> RequisicaoWorklistItem:
    is_rascunho = req.status == StatusRequisicao.RASCUNHO
    beneficiario = req.beneficiario
    is_terceiro = beneficiario is not None and beneficiario.pk != user.pk
    total_itens = len(req.itens.all())
    resumo = f"{total_itens} item" if total_itens == 1 else f"{total_itens} itens"
    return RequisicaoWorklistItem(
        id=req.pk,
        detail_url=None,  # TODO: implement detail_url/can_view_detail when detail view is ready
        is_rascunho=is_rascunho,
        numero_publico=req.numero_publico or None,
        status_value=req.status,
        status_label=req.get_status_display(),
        status_variant=_STATUS_VARIANT.get(req.status, "neutral"),
        data_label=_data_label(req),
        is_beneficiario_terceiro=is_terceiro,
        beneficiario_nome=beneficiario.nome_completo if is_terceiro else None,
        resumo_itens=resumo,
        can_view_detail=False,
    )
