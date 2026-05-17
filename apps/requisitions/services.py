from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.requisitions import data, idempotency
from apps.requisitions.contexts import (
    ContextoAtendimento,
    ContextoAutorizacao,
    ContextoCancelamento,
    ContextoEnvio,
)
from apps.requisitions.domain import validation
from apps.requisitions.domain.state_machine import apply_transition
from apps.requisitions.domain.types import (
    ItemAtendimentoData,
    ItemAutorizacaoData,
    ItemRascunhoData,
)
from apps.requisitions.idempotency import get_or_create_idempotency_record, handle_idempotency
from apps.requisitions.models import (
    Requisicao,
    StatusIdempotencia,
    StatusRequisicao,
)
from apps.requisitions.policies import (
    pode_criar_requisicao_para,
    pode_manipular_pre_autorizacao,
    pode_retirar_requisicao,
    pode_ver_fila_atendimento,
    pode_visualizar_requisicao,
    queryset_fila_atendimento,
    queryset_fila_autorizacao,
)
from apps.requisitions.ports import StockPort
from apps.requisitions.sequences import gerar_numero_publico
from apps.users.models import PapelChoices

User = get_user_model()
IDEMPOTENCY_ENDPOINT_FULFILL = "requisitions_fulfill"
IDEMPOTENCY_ENDPOINT_PICKUP = "requisitions_pickup"

ItemAtendimentoPayload = ItemAtendimentoData | dict[str, object]


def _get_default_stock() -> StockPort:
    from apps.stock.adapters import StockAdapter

    return StockAdapter()


def criar_rascunho_requisicao(
    *,
    criador: User,
    beneficiario: User,
    observacao: str,
    itens: list[ItemRascunhoData],
) -> Requisicao:
    if not pode_criar_requisicao_para(criador, beneficiario):
        raise PermissionDenied(
            "Usuário sem permissão para criar requisição para este beneficiário."
        )
    validation.validar_beneficiario_setor(beneficiario)
    materiais = validation._validar_itens_rascunho(itens)
    with transaction.atomic():
        requisicao = Requisicao.objects.create(
            criador=criador, beneficiario=beneficiario, observacao=observacao
        )
        data.bulk_create_itens(requisicao, itens, materiais)
    return data.recarregar_rascunho(requisicao.pk)


def atualizar_rascunho_requisicao(
    *,
    requisicao_id: int,
    ator: User,
    beneficiario_id: int,
    observacao: str,
    itens: list[ItemRascunhoData],
) -> Requisicao:
    with transaction.atomic():
        try:
            requisicao = (
                Requisicao.objects.select_related("criador", "beneficiario", "setor_beneficiario")
                .select_for_update(of=("self",))
                .prefetch_related("itens__material", "eventos__usuario")
                .get(pk=requisicao_id)
            )
        except Requisicao.DoesNotExist as exc:
            raise NotFound("Requisição não encontrada.") from exc
        if not pode_visualizar_requisicao(ator, requisicao):
            raise NotFound("Requisição não encontrada.")
        if not pode_manipular_pre_autorizacao(ator, requisicao):
            raise PermissionDenied("Apenas criador pode editar a requisição.")
        validation.validar_status_rascunho_para_edicao(requisicao)
        beneficiario, setor = data.carregar_beneficiario_e_setor(beneficiario_id)
        validation.validar_beneficiario_setor_ativo(beneficiario, setor)
        if not pode_criar_requisicao_para(ator, beneficiario):
            raise PermissionDenied(
                "Usuário sem permissão para criar requisição para este beneficiário."
            )
        materiais = validation._validar_itens_rascunho(itens)
        data.aplicar_edicao_rascunho(requisicao, beneficiario, setor, observacao, itens, materiais)
    return data.recarregar_rascunho(requisicao_id)


def enviar_para_autorizacao(*, requisicao: Requisicao, ator: User) -> Requisicao:
    with ContextoEnvio.abrir(requisicao, ator) as ctx:
        validation.validar_envio_para_autorizacao(list(ctx.requisicao.itens.all()))
        if ctx.is_primeiro_envio:
            transicao = "enviar_para_autorizacao"
            payload = {
                "numero_publico": gerar_numero_publico(),
                "data_envio_autorizacao": timezone.now(),
            }
        else:
            transicao = "reenviar_para_autorizacao"
            payload = {}
        apply_transition(
            requisicao=ctx.requisicao, transition_name=transicao, actor=ctx.ator, payload=payload
        )
    return data.recarregar_rascunho(requisicao.pk)


def retornar_para_rascunho(*, requisicao: Requisicao, ator: User) -> Requisicao:
    with transaction.atomic():
        try:
            requisicao = (
                Requisicao.objects.select_for_update(of=("self",))
                .select_related("criador", "beneficiario", "setor_beneficiario")
                .prefetch_related("itens__material__estoque", "eventos__usuario")
                .get(pk=requisicao.pk)
            )
        except Requisicao.DoesNotExist as exc:
            raise NotFound("Requisição não encontrada.") from exc
        if not pode_visualizar_requisicao(ator, requisicao):
            raise NotFound("Requisição não encontrada.")
        if not pode_manipular_pre_autorizacao(ator, requisicao):
            raise PermissionDenied("Apenas criador ou beneficiário podem retornar a requisição.")
        apply_transition(
            requisicao=requisicao, transition_name="retornar_para_rascunho", actor=ator, payload={}
        )
    return data.recarregar_rascunho(requisicao.pk)


def descartar_rascunho_nunca_enviado(*, requisicao: Requisicao, ator: User) -> None:
    with transaction.atomic():
        requisicao = (
            Requisicao.objects.select_for_update().prefetch_related("itens").get(pk=requisicao.pk)
        )
        if not pode_manipular_pre_autorizacao(ator, requisicao):
            raise PermissionDenied("Apenas criador pode descartar a requisição.")
        validation.validar_descarte_rascunho(requisicao)
        requisicao.itens.all().delete()
        requisicao.delete()


def cancelar_requisicao(
    *,
    requisicao: Requisicao,
    ator: User,
    motivo_cancelamento: str,
    stock: StockPort | None = None,
) -> Requisicao:
    if stock is None:
        stock = _get_default_stock()
    with ContextoCancelamento.abrir(requisicao, ator) as ctx:
        if ctx.requer_liberacao_estoque:
            motivo_cancelamento = validation.validar_motivo(
                motivo_cancelamento,
                "motivo_cancelamento",
                "Motivo do cancelamento é obrigatório.",
            )
            itens_requisicao = data.carregar_itens_bloqueados(ctx.requisicao)
            itens_autorizados = [i for i in itens_requisicao if i.quantidade_autorizada > 0]
            validation.validar_itens_autorizados_existem(itens_autorizados, ctx.requisicao)
            apply_transition(
                requisicao=ctx.requisicao,
                transition_name="cancelar_pos_autorizacao_sem_saldo",
                actor=ctx.ator,
                payload={
                    "responsavel_atendimento": ctx.ator,
                    "data_finalizacao": timezone.now(),
                    "motivo_cancelamento": motivo_cancelamento,
                },
            )
            stock.liberar_reservas_cancelamento(ctx.requisicao, itens_autorizados)
        else:
            validation.validar_status_cancelamento_pre(ctx.requisicao)
            apply_transition(
                requisicao=ctx.requisicao,
                transition_name="cancelar_pre_autorizacao",
                actor=ctx.ator,
                payload={"data_finalizacao": timezone.now()},
            )
    return data.recarregar_atendido(requisicao.pk)


def autorizar_requisicao(
    *,
    requisicao: Requisicao,
    ator: User,
    itens: list[ItemAutorizacaoData],
    stock: StockPort | None = None,
) -> Requisicao:
    if stock is None:
        stock = _get_default_stock()
    with ContextoAutorizacao.abrir(requisicao, ator) as ctx:
        itens_requisicao = data.carregar_itens_bloqueados(ctx.requisicao)
        itens_por_id = validation._validar_itens_autorizacao(
            itens_requisicao=itens_requisicao, itens=itens
        )
        data.aplicar_quantidades_autorizacao(itens_requisicao, itens_por_id)
        transicao = "autorizar_total"
        if any(i.quantidade_autorizada < i.quantidade_solicitada for i in itens_requisicao):
            transicao = "autorizar_parcial"
        apply_transition(
            requisicao=ctx.requisicao,
            transition_name=transicao,
            actor=ctx.ator,
            payload={"chefe_autorizador": ctx.ator, "data_autorizacao_ou_recusa": timezone.now()},
        )
        itens_autorizados = [i for i in itens_requisicao if i.quantidade_autorizada > 0]
        if itens_autorizados:
            stock.aplicar_reservas_autorizacao(ctx.requisicao, itens_autorizados)
    return data.recarregar_autorizado(requisicao.pk)


def recusar_requisicao(*, requisicao: Requisicao, ator: User, motivo_recusa: str) -> Requisicao:
    motivo_recusa = validation.validar_motivo(
        motivo_recusa, "motivo_recusa", "Motivo da recusa é obrigatório."
    )
    with ContextoAutorizacao.abrir(requisicao, ator) as ctx:
        apply_transition(
            requisicao=ctx.requisicao,
            transition_name="recusar",
            actor=ctx.ator,
            payload={
                "chefe_autorizador": ctx.ator,
                "motivo_recusa": motivo_recusa,
                "data_autorizacao_ou_recusa": timezone.now(),
            },
        )
    return data.recarregar_autorizado(requisicao.pk)


def listar_fila_autorizacao(*, ator: User):
    if not ator.is_authenticated:
        raise PermissionDenied("Usuário precisa estar autenticado para ver a fila de autorizações.")
    if ator.is_superuser or not ator.is_active:
        raise PermissionDenied("Usuário sem permissão para acessar a fila de autorizações.")
    if ator.papel not in (PapelChoices.CHEFE_SETOR, PapelChoices.CHEFE_ALMOXARIFADO):
        raise PermissionDenied("Usuário sem permissão para acessar a fila de autorizações.")
    return (
        queryset_fila_autorizacao(ator)
        .filter(status=StatusRequisicao.AGUARDANDO_AUTORIZACAO)
        .select_related("criador", "beneficiario", "setor_beneficiario")
        .prefetch_related("itens__material")
        .order_by("data_envio_autorizacao", "id")
    )


def listar_fila_atendimento(*, ator: User):
    if not ator.is_authenticated:
        raise PermissionDenied("Usuário precisa estar autenticado para ver a fila de atendimento.")
    if not pode_ver_fila_atendimento(ator):
        raise PermissionDenied("Usuário sem permissão para acessar a fila de atendimento.")
    return (
        queryset_fila_atendimento(ator)
        .select_related("criador", "beneficiario", "setor_beneficiario", "chefe_autorizador")
        .prefetch_related("itens__material")
        .order_by("data_autorizacao_ou_recusa", "id")
    )


def atender_requisicao(
    *,
    requisicao: Requisicao,
    ator: User,
    itens: list[ItemAtendimentoPayload] | None = None,
    observacao_atendimento: str = "",
) -> Requisicao:
    itens_norm = idempotency.normalizar_itens(itens)
    if itens_norm is None:
        return atender_requisicao_completa(
            requisicao=requisicao, ator=ator, observacao_atendimento=observacao_atendimento
        )
    return atender_requisicao_com_itens(
        requisicao=requisicao,
        ator=ator,
        itens=itens_norm,
        observacao_atendimento=observacao_atendimento,
    )


def atender_requisicao_idempotente(
    *,
    requisicao: Requisicao,
    ator: User,
    idempotency_key: str,
    itens: list[ItemAtendimentoPayload] | None = None,
    observacao_atendimento: str = "",
) -> Requisicao:
    itens_norm = idempotency.normalizar_itens(itens)
    payload_hash = idempotency.hash_payload_atendimento(
        itens=itens_norm, observacao_atendimento=observacao_atendimento
    )
    with transaction.atomic():
        registro, criado = get_or_create_idempotency_record(
            usuario=ator,
            requisicao=requisicao,
            operation=IDEMPOTENCY_ENDPOINT_FULFILL,
            key=idempotency_key,
            payload_hash=payload_hash,
        )
        cached = handle_idempotency(
            registro,
            criado,
            payload_hash,
            idempotency_key,
            IDEMPOTENCY_ENDPOINT_FULFILL,
            "Atendimento com esta chave de idempotência ainda está em processamento.",
            lambda: data.recarregar_detalhe(requisicao.id),
        )
        if cached is not None:
            return cached
        resultado = atender_requisicao(
            requisicao=requisicao,
            ator=ator,
            itens=itens_norm,
            observacao_atendimento=observacao_atendimento,
        )
        registro.status = StatusIdempotencia.COMPLETED
        registro.save(update_fields=["status", "updated_at"])
    return resultado


def atender_requisicao_completa(
    *,
    requisicao: Requisicao,
    ator: User,
    observacao_atendimento: str = "",
) -> Requisicao:
    with ContextoAtendimento.abrir(requisicao, ator) as ctx:
        itens_requisicao = data.carregar_itens_bloqueados(ctx.requisicao)
        itens_autorizados = [i for i in itens_requisicao if i.quantidade_autorizada > 0]
        validation.validar_itens_autorizados_existem(itens_autorizados, ctx.requisicao)
        data.aplicar_itens_atendimento_completo(itens_autorizados)
        apply_transition(
            requisicao=ctx.requisicao,
            transition_name="atender_total",
            actor=ctx.ator,
            payload={
                "responsavel_atendimento": ctx.ator,
                "data_finalizacao": timezone.now(),
                "observacao_atendimento": observacao_atendimento.strip(),
            },
        )
    return data.recarregar_atendido(requisicao.pk)


def atender_requisicao_com_itens(
    *,
    requisicao: Requisicao,
    ator: User,
    itens: list[ItemAtendimentoData],
    observacao_atendimento: str = "",
) -> Requisicao:
    with ContextoAtendimento.abrir(requisicao, ator) as ctx:
        itens_requisicao = data.carregar_itens_bloqueados(ctx.requisicao)
        itens_autorizados = [i for i in itens_requisicao if i.quantidade_autorizada > 0]
        validation.validar_itens_autorizados_existem(itens_autorizados, ctx.requisicao)
        dados_por_item_id, atendimento_parcial = validation.validar_itens_atendimento(
            itens, itens_autorizados
        )
        data.aplicar_itens_atendimento_parcial(itens_autorizados, dados_por_item_id)
        apply_transition(
            requisicao=ctx.requisicao,
            transition_name="atender_parcial" if atendimento_parcial else "atender_total",
            actor=ctx.ator,
            payload={
                "responsavel_atendimento": ctx.ator,
                "data_finalizacao": timezone.now(),
                "observacao_atendimento": observacao_atendimento.strip(),
            },
        )
    return data.recarregar_atendido(requisicao.pk)


def retirar_requisicao(
    *,
    requisicao: Requisicao,
    ator: User,
    retirante_fisico: str,
    stock: StockPort | None = None,
) -> Requisicao:
    if stock is None:
        stock = _get_default_stock()
    with transaction.atomic():
        requisicao = (
            Requisicao.objects.select_for_update()
            .select_related("criador", "beneficiario", "setor_beneficiario")
            .get(pk=requisicao.pk)
        )
        if not pode_visualizar_requisicao(ator, requisicao):
            raise NotFound("Requisição não encontrada.")
        if not pode_retirar_requisicao(ator, requisicao):
            raise PermissionDenied(
                "Usuário sem permissão para registrar retirada desta requisição."
            )
        retirante_fisico_normalizado = validation.validar_retirante(retirante_fisico)
        itens_requisicao = data.carregar_itens_bloqueados(requisicao)
        validation.validar_consistencia_itens_retirada(itens_requisicao)
        apply_transition(
            requisicao=requisicao,
            transition_name="retirar",
            actor=ator,
            payload={
                "retirante_fisico": retirante_fisico_normalizado,
                "data_retirada": timezone.now(),
            },
        )
        itens_autorizados = [i for i in itens_requisicao if i.quantidade_autorizada > 0]
        if itens_autorizados:
            stock.aplicar_saidas_e_liberacoes_retirada(requisicao, itens_autorizados)
    return data.recarregar_detalhe(requisicao.pk)


def retirar_requisicao_idempotente(
    *,
    requisicao: Requisicao,
    ator: User,
    idempotency_key: str,
    retirante_fisico: str,
) -> Requisicao:
    payload_hash = idempotency.hash_payload_retirada(retirante_fisico)
    with transaction.atomic():
        registro, criado = get_or_create_idempotency_record(
            usuario=ator,
            requisicao=requisicao,
            operation=IDEMPOTENCY_ENDPOINT_PICKUP,
            key=idempotency_key,
            payload_hash=payload_hash,
        )
        cached = handle_idempotency(
            registro,
            criado,
            payload_hash,
            idempotency_key,
            IDEMPOTENCY_ENDPOINT_PICKUP,
            "Retirada com esta chave de idempotência ainda está em processamento.",
            lambda: data.recarregar_detalhe(requisicao.id),
        )
        if cached is not None:
            return cached
        resultado = retirar_requisicao(
            requisicao=requisicao, ator=ator, retirante_fisico=retirante_fisico
        )
        registro.status = StatusIdempotencia.COMPLETED
        registro.save(update_fields=["status", "updated_at"])
    return resultado
