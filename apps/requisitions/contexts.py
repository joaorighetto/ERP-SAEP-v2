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
