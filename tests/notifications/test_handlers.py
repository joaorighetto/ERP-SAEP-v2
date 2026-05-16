import pytest

import apps.core.events as core_events
from apps.core.events import _subscribers, clear_subscribers, publish
from apps.notifications.handlers import handle_requisicao_event, register_event_handlers
from apps.notifications.services import notificar
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
        saved_subs = {k: list(v) for k, v in _subscribers.items()}
        saved_enum = set(core_events._enum_registrations)
        clear_subscribers()
        yield
        clear_subscribers()
        for k, v in saved_subs.items():
            _subscribers[k].extend(v)
        core_events._enum_registrations.update(saved_enum)

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

    def test_register_event_handlers_idempotente(self, monkeypatch):
        chamadas = []
        monkeypatch.setattr("apps.notifications.handlers.notificar", lambda *a: chamadas.append(a))
        register_event_handlers()
        register_event_handlers()

        publish(RequisicaoEvent.CANCELADA, {"requisicao_id": 1, "actor_id": 2})

        assert len(chamadas) == 1, "duplo register não deve duplicar handlers"

    def test_payload_invalido_nao_chama_notificar(self, monkeypatch):
        chamadas = []
        monkeypatch.setattr("apps.notifications.handlers.notificar", lambda *a: chamadas.append(a))
        register_event_handlers()

        # actor_id ausente → TypeError no wrapper; publish silencia a exceção
        publish(RequisicaoEvent.AUTORIZADA, {"requisicao_id": 99})

        assert chamadas == [], "payload inválido não deve disparar notificar"

    def test_evento_fora_do_dominio_nao_chama_notificar(self, monkeypatch):
        chamadas = []
        monkeypatch.setattr("apps.notifications.handlers.notificar", lambda *a: chamadas.append(a))
        register_event_handlers()

        publish("evento_desconhecido", {"requisicao_id": 1, "actor_id": 2})

        assert chamadas == [], "evento fora do domínio RequisicaoEvent não deve disparar notificar"


class TestNotificar:
    def test_isola_excecao_de_carga(self, monkeypatch):
        monkeypatch.setattr(
            "apps.notifications.services._carregar_requisicao_para_notificacao",
            lambda _: (_ for _ in ()).throw(Exception("DB indisponível")),
        )

        # não deve propagar — falha de notificação não pode quebrar o fluxo chamador
        notificar(RequisicaoEvent.AUTORIZADA, requisicao_id=1, actor_id=2)

    def test_isola_excecao_do_handler(self, monkeypatch):
        fake_req = object()
        monkeypatch.setattr(
            "apps.notifications.services._carregar_requisicao_para_notificacao",
            lambda _: fake_req,
        )
        monkeypatch.setattr(
            "apps.notifications.services._NOTIF_ROUTING",
            {RequisicaoEvent.AUTORIZADA: lambda _: (_ for _ in ()).throw(RuntimeError("boom"))},
        )

        notificar(RequisicaoEvent.AUTORIZADA, requisicao_id=1, actor_id=2)
