from apps.core.events import PUSH_LEMBRETE_AUTORIZACOES_ATRASADAS, subscribe
from apps.notifications.services import enviar_push_payload_usuario, notificar
from apps.requisitions.events import RequisicaoEvent


def handle_requisicao_event(event: RequisicaoEvent, requisicao_id: int, actor_id: int) -> None:
    notificar(event, requisicao_id, actor_id)


def _enviar_lembrete_autorizacoes_atrasadas(payload: dict[str, object]) -> None:
    enviar_push_payload_usuario(
        usuario_id=payload["usuario_id"],
        payload=payload["payload"],
        ttl=payload["ttl"],
    )


def register_event_handlers() -> None:
    subscribe(RequisicaoEvent, handle_requisicao_event)
    subscribe(PUSH_LEMBRETE_AUTORIZACOES_ATRASADAS, _enviar_lembrete_autorizacoes_atrasadas)
