import logging
from collections import defaultdict
from collections.abc import Callable
from functools import partial
from typing import Any

from django.db import transaction

logger = logging.getLogger(__name__)

REQUISICAO_ENVIADA_AUTORIZACAO = "requisicao.enviada_autorizacao"
REQUISICAO_AUTORIZADA = "requisicao.autorizada"
REQUISICAO_RECUSADA = "requisicao.recusada"
REQUISICAO_CANCELADA = "requisicao.cancelada"
REQUISICAO_PRONTA_PARA_RETIRADA = "requisicao.pronta_para_retirada"
REQUISICAO_RETIRADA = "requisicao.retirada"
PUSH_LEMBRETE_AUTORIZACOES_ATRASADAS = "push.lembrete_autorizacoes_atrasadas"

EventPayload = dict[str, Any]
EventHandler = Callable[[EventPayload], None]

_subscribers: dict[str, list[EventHandler]] = defaultdict(list)


def _subscribe_single(event_name: str, handler: EventHandler) -> None:
    handlers = _subscribers[event_name]
    if handler not in handlers:
        handlers.append(handler)


def subscribe(event_name_or_enum, handler: EventHandler | None = None):
    """Register handler for an event.

    Two forms:
      subscribe("event.name", handler_fn)         — direct registration
      @subscribe(SomeStrEnumClass)                 — decorator; registers for all enum
                                                     values, calling handler(event, **payload)
    """
    if handler is not None:
        _subscribe_single(str(event_name_or_enum), handler)
        return

    target = event_name_or_enum

    def decorator(fn):
        if isinstance(target, type) and issubclass(target, str):
            for event in target:
                _event = event

                def _wrapper(payload, e=_event, f=fn):
                    f(e, **payload)

                _subscribe_single(str(_event), _wrapper)
        else:
            _subscribe_single(str(target), fn)
        return fn

    return decorator


def clear_subscribers() -> None:
    _subscribers.clear()


def publish(event_name: str, payload: EventPayload) -> None:
    for handler in tuple(_subscribers[event_name]):
        try:
            handler(payload)
        except Exception:
            logger.exception("Falha ao processar evento %s", event_name)


def publish_on_commit(event_name: str, payload: EventPayload) -> None:
    transaction.on_commit(partial(publish, event_name, payload))
