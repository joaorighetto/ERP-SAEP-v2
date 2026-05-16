from django.db import connection, transaction

from apps.core.api.exceptions import DomainConflict
from apps.core.events import publish_on_commit
from apps.requisitions.events import RequisicaoEvent
from apps.requisitions.models import EventoTimeline, Requisicao, StatusRequisicao, TipoEvento

TRANSICOES_REQUISICAO: dict[str, dict[str, object]] = {
    "autorizar_total": {
        "from_status": (StatusRequisicao.AGUARDANDO_AUTORIZACAO,),
        "to_status": StatusRequisicao.AUTORIZADA,
        "timeline_event_type": TipoEvento.AUTORIZACAO_TOTAL,
        "audit_fields_to_set": (
            "chefe_autorizador",
            "data_autorizacao_ou_recusa",
            "status",
        ),
        "side_effects": (),
        "notification_event": RequisicaoEvent.AUTORIZADA,
    },
    "autorizar_parcial": {
        "from_status": (StatusRequisicao.AGUARDANDO_AUTORIZACAO,),
        "to_status": StatusRequisicao.AUTORIZADA,
        "timeline_event_type": TipoEvento.AUTORIZACAO_PARCIAL,
        "audit_fields_to_set": (
            "chefe_autorizador",
            "data_autorizacao_ou_recusa",
            "status",
        ),
        "side_effects": (),
        "notification_event": RequisicaoEvent.AUTORIZADA,
    },
    "recusar": {
        "from_status": (StatusRequisicao.AGUARDANDO_AUTORIZACAO,),
        "to_status": StatusRequisicao.RECUSADA,
        "timeline_event_type": TipoEvento.RECUSA,
        "audit_fields_to_set": (
            "chefe_autorizador",
            "data_autorizacao_ou_recusa",
            "motivo_recusa",
            "status",
        ),
        "side_effects": (),
        "notification_event": RequisicaoEvent.RECUSADA,
    },
    "atender_total": {
        "from_status": (StatusRequisicao.AUTORIZADA,),
        "to_status": StatusRequisicao.PRONTA_PARA_RETIRADA,
        "timeline_event_type": TipoEvento.ATENDIMENTO,
        "audit_fields_to_set": (
            "responsavel_atendimento",
            "data_finalizacao",
            "observacao_atendimento",
            "status",
        ),
        "side_effects": (),
        "notification_event": RequisicaoEvent.ATENDIDA,
    },
    "atender_parcial": {
        "from_status": (StatusRequisicao.AUTORIZADA,),
        "to_status": StatusRequisicao.PRONTA_PARA_RETIRADA_PARCIAL,
        "timeline_event_type": TipoEvento.ATENDIMENTO_PARCIAL,
        "audit_fields_to_set": (
            "responsavel_atendimento",
            "data_finalizacao",
            "observacao_atendimento",
            "status",
        ),
        "side_effects": (),
        "notification_event": RequisicaoEvent.ATENDIDA_PARCIALMENTE,
    },
    "retirar": {
        "from_status": (
            StatusRequisicao.PRONTA_PARA_RETIRADA,
            StatusRequisicao.PRONTA_PARA_RETIRADA_PARCIAL,
        ),
        "to_status": StatusRequisicao.RETIRADA,
        "timeline_event_type": TipoEvento.RETIRADA,
        "audit_fields_to_set": (
            "retirante_fisico",
            "data_retirada",
            "status",
        ),
        "side_effects": (),
        "notification_event": None,
    },
    "cancelar_pos_autorizacao_sem_saldo": {
        "from_status": (StatusRequisicao.AUTORIZADA,),
        "to_status": StatusRequisicao.CANCELADA,
        "timeline_event_type": TipoEvento.CANCELAMENTO,
        "audit_fields_to_set": (
            "responsavel_atendimento",
            "data_finalizacao",
            "motivo_cancelamento",
            "status",
        ),
        "side_effects": (),
        "notification_event": RequisicaoEvent.CANCELADA,
    },
    "cancelar_pre_autorizacao": {
        "from_status": (
            StatusRequisicao.RASCUNHO,
            StatusRequisicao.AGUARDANDO_AUTORIZACAO,
        ),
        "to_status": StatusRequisicao.CANCELADA,
        "timeline_event_type": TipoEvento.CANCELAMENTO,
        "audit_fields_to_set": (
            "data_finalizacao",
            "status",
        ),
        "side_effects": (),
        "notification_event": RequisicaoEvent.CANCELADA,
    },
    "enviar_para_autorizacao": {
        "from_status": (StatusRequisicao.RASCUNHO,),
        "to_status": StatusRequisicao.AGUARDANDO_AUTORIZACAO,
        "timeline_event_type": TipoEvento.ENVIO_AUTORIZACAO,
        "audit_fields_to_set": ("numero_publico", "data_envio_autorizacao", "status"),
        "side_effects": (),
        "notification_event": RequisicaoEvent.ENVIADA,
    },
    "reenviar_para_autorizacao": {
        "from_status": (StatusRequisicao.RASCUNHO,),
        "to_status": StatusRequisicao.AGUARDANDO_AUTORIZACAO,
        "timeline_event_type": TipoEvento.REENVIO_AUTORIZACAO,
        "audit_fields_to_set": ("status",),
        "side_effects": (),
        "notification_event": RequisicaoEvent.ENVIADA,
    },
    "retornar_para_rascunho": {
        "from_status": (StatusRequisicao.AGUARDANDO_AUTORIZACAO,),
        "to_status": StatusRequisicao.RASCUNHO,
        "timeline_event_type": TipoEvento.RETORNO_RASCUNHO,
        "audit_fields_to_set": ("status",),
        "side_effects": (),
        "notification_event": None,
    },
}


def _publish_notification(event: RequisicaoEvent, requisicao: Requisicao, actor) -> None:
    if not transaction.get_connection().in_atomic_block:
        raise DomainConflict(
            "Publicação de notificação de requisição exige transação ativa.",
            details={"requisicao_id": requisicao.pk, "event": event},
        )
    publish_on_commit(event, {"requisicao_id": requisicao.pk, "actor_id": actor.pk})


def apply_transition(
    requisicao: Requisicao,
    transition_name: str,
    actor,
    *,
    payload: dict[str, object],
) -> Requisicao:
    if not connection.in_atomic_block:
        raise DomainConflict(
            "apply_transition exige transação ativa.",
            details={"transition_name": transition_name},
        )
    config = TRANSICOES_REQUISICAO[transition_name]

    if requisicao.status not in config["from_status"]:
        raise DomainConflict(
            "Transição inválida para o status atual da requisição.",
            details={"status_atual": requisicao.status, "transicao": transition_name},
        )

    for field_name in config["audit_fields_to_set"]:
        if field_name == "status":
            setattr(requisicao, field_name, config["to_status"])
            continue
        setattr(requisicao, field_name, payload[field_name])

    requisicao.full_clean()
    requisicao.save(
        update_fields=[
            *config["audit_fields_to_set"],
            "updated_at",
        ]
    )
    EventoTimeline.objects.create(
        requisicao=requisicao,
        tipo_evento=config["timeline_event_type"],
        usuario=actor,
    )

    for side_effect in config["side_effects"]:
        side_effect(requisicao, payload)

    notification_event = config.get("notification_event")
    if notification_event:
        _publish_notification(notification_event, requisicao, actor)

    return requisicao
