import pytest

from apps.core.events import _subscribers, clear_subscribers, publish
from apps.notifications.handlers import handle_requisicao_event, register_event_handlers
from apps.requisitions.events import RequisicaoEvent


class TestHandleRequisicaoEvent:
    def test_delega_para_notificar_com_evento_e_args_corretos(self, monkeypatch):
        chamadas = []
        monkeypatch.setattr("apps.notifications.handlers.notificar", lambda *a: chamadas.append(a))

        handle_requisicao_event(RequisicaoEvent.ENVIADA, requisicao_id=42, actor_id=7)

        assert chamadas == [(RequisicaoEvent.ENVIADA, 42, 7)]

    @pytest.mark.parametrize("event", list(RequisicaoEvent))
    def test_repassa_cada_evento_para_notificar(self, monkeypatch, event):
        chamadas = []
        monkeypatch.setattr("apps.notifications.handlers.notificar", lambda *a: chamadas.append(a))

        handle_requisicao_event(event, requisicao_id=1, actor_id=2)

        assert chamadas == [(event, 1, 2)]


class TestRegisterEventHandlers:
    @pytest.fixture(autouse=True)
    def isolate_subscribers(self):
        saved = {k: list(v) for k, v in _subscribers.items()}
        clear_subscribers()
        yield
        clear_subscribers()
        for k, v in saved.items():
            _subscribers[k].extend(v)

    def test_registra_handler_para_cada_valor_de_requisicao_event(self, monkeypatch):
        chamadas = []
        monkeypatch.setattr("apps.notifications.handlers.notificar", lambda *a: chamadas.append(a))
        register_event_handlers()

        for event in RequisicaoEvent:
            publish(event, {"requisicao_id": 10, "actor_id": 3})

        assert len(chamadas) == len(RequisicaoEvent)
        eventos_chamados = {c[0] for c in chamadas}
        assert eventos_chamados == set(RequisicaoEvent)

    def test_handler_recebe_requisicao_id_e_actor_id_do_payload(self, monkeypatch):
        chamadas = []
        monkeypatch.setattr("apps.notifications.handlers.notificar", lambda *a: chamadas.append(a))
        register_event_handlers()

        publish(RequisicaoEvent.AUTORIZADA, {"requisicao_id": 99, "actor_id": 55})

        assert chamadas == [(RequisicaoEvent.AUTORIZADA, 99, 55)]
