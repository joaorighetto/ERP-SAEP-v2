# Plan: Issue #81 — RequisicaoEvent enum + entrypoint único notificar()

## Scope

**Muda:**
- `apps/requisitions/events.py` — novo arquivo com `RequisicaoEvent(str, Enum)`
- `apps/core/events.py` — `subscribe()` estendida para suportar `@subscribe(EnumClass)`
- `apps/notifications/services.py` — adiciona `notificar()` com routing table interna
- `apps/notifications/handlers.py` — substitui 6 handlers individuais por `@subscribe(RequisicaoEvent)`
- `apps/requisitions/domain/state_machine.py` — usa `RequisicaoEvent` em vez das constantes de string; passa `actor_id` no payload

**NÃO muda:**
- Funções auxiliares de `notifications/services.py` usadas por views e testes (`criar_notificacao_usuario`, `criar_notificacao_papel`, etc.)
- `notifications/views.py`
- Qualquer arquivo de teste existente

## Files touched

- `apps/requisitions/events.py` (novo)
- `apps/core/events.py`
- `apps/notifications/services.py`
- `apps/notifications/handlers.py`
- `apps/requisitions/domain/state_machine.py`
- `tests/notifications/test_handlers.py` (novo)

## Mapeamento de eventos

| Transição state_machine         | Antes (string)                    | Depois (enum)                         |
|---------------------------------|-----------------------------------|---------------------------------------|
| enviar_para_autorizacao         | REQUISICAO_ENVIADA_AUTORIZACAO    | RequisicaoEvent.ENVIADA               |
| reenviar_para_autorizacao       | REQUISICAO_ENVIADA_AUTORIZACAO    | RequisicaoEvent.ENVIADA               |
| autorizar_total                 | REQUISICAO_AUTORIZADA             | RequisicaoEvent.AUTORIZADA            |
| autorizar_parcial               | REQUISICAO_AUTORIZADA             | RequisicaoEvent.AUTORIZADA            |
| recusar                         | REQUISICAO_RECUSADA               | RequisicaoEvent.RECUSADA              |
| atender_total                   | REQUISICAO_PRONTA_PARA_RETIRADA   | RequisicaoEvent.ATENDIDA              |
| atender_parcial                 | REQUISICAO_PRONTA_PARA_RETIRADA   | RequisicaoEvent.ATENDIDA_PARCIALMENTE |
| cancelar_*                      | REQUISICAO_CANCELADA              | RequisicaoEvent.CANCELADA             |
| retirar                         | REQUISICAO_RETIRADA               | None (removido — não está no enum)    |
| retornar_para_rascunho          | None                              | None                                  |

## Routing table em notificar()

```
ENVIADA           → notifica chefe_responsavel; envia push aguardando_autorizacao
AUTORIZADA        → notifica criador+beneficiario; notifica roles almoxarifado
RECUSADA          → notifica criador+beneficiario
ATENDIDA          → notifica criador+beneficiario (pronta para retirada)
ATENDIDA_PARCIALMENTE → notifica criador+beneficiario (pronta para retirada parcial)
CANCELADA         → notifica criador+beneficiario
```

## Mudança no subscribe()

```python
# Suporta:
# 1. subscribe(str, handler) — forma atual, inalterada
# 2. @subscribe(EnumClass)   — novo: registra para todos os valores do enum
#    handler chamado com (event: EnumMember, **payload_dict)
```

## Test strategy

Novo `tests/notifications/test_handlers.py`:
- Para cada `RequisicaoEvent`: mock `notificar`, dispara `publish(event, payload)`, verifica `notificar` chamado com args corretos
- Testa que `handle_requisicao_event` delega para `notificar()` com event correto

## Invariants preserved

- `notifications` importa de `requisitions.events`; nunca o inverso
- Falha em `notificar()` loga, não reverte (publish_on_commit garante)
- `actor_id` incluído no payload para completude do contrato, mas notificações atuais não o usam
- Funções auxiliares de `services.py` mantidas públicas (usadas por views e testes)

## Risks

- Remoção de `REQUISICAO_RETIRADA` do bus: `retirar` transição para de emitir evento. Testes existentes não assertam criação de notificação para retirada, apenas idempotência (count não aumenta).
- Constantes antigas em `core/events.py` mantidas para evitar quebrar imports de terceiros; apenas removidas de `state_machine.py`.
