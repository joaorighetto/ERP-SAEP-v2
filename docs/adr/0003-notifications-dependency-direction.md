# ADR 0003 — Direção de dependência entre requisitions e notifications

## Status

Aceita.

## Contexto

O módulo `notifications` expõe 17 funções públicas em `apps/notifications/services.py`. Callers em `apps/requisitions/services.py` montam payloads, decidem entre `criar_notificacao_usuario` e `criar_notificacao_papel`, e escolhem a função certa por convenção implícita. A interface é tão larga quanto a implementação — o módulo não tem leverage.

A refatoração proposta concentra tudo em um único entrypoint:

```python
# apps/notifications/services.py
def notificar(event: RequisicaoEvent, requisicao_id: int, actor_id: int) -> None: ...
```

A decisão crítica é: onde o enum `RequisicaoEvent` vive, e qual direção de dependência isso implica.

Duas opções foram avaliadas:

**A — Enum em `apps/requisitions/events.py`**
`notifications` importa o enum de `requisitions`. Direção: `notifications → requisitions`.

**B — Enum em `apps/notifications/`**
`requisitions` importa o enum de `notifications` para publicar eventos. Direção: `requisitions → notifications`.

## Decisão

Adotada a **Opção A — enum em `apps/requisitions/events.py`**.

### Por que Option B foi rejeitada

Na Opção B, `requisitions` importa de `notifications` apenas para nomear o evento que vai publicar. Isso acopla o domínio de requisições ao módulo de entrega de notificações — um detalhe de infraestrutura. Se `notifications` for removido, renomeado ou substituído, `requisitions` quebra.

### Decisões de design

**Localização do enum**

```python
# apps/requisitions/events.py
class RequisicaoEvent(str, Enum):
    ENVIADA = "requisicao.enviada"
    AUTORIZADA = "requisicao.autorizada"
    RECUSADA = "requisicao.recusada"
    ATENDIDA = "requisicao.atendida"
    ATENDIDA_PARCIALMENTE = "requisicao.atendida_parcialmente"
    CANCELADA = "requisicao.cancelada"
```

`RequisicaoEvent` é um fato de domínio — nomeia o que aconteceu no fluxo de requisição, não como será entregue. Pertence a `requisitions`.

**Fluxo de publicação**

O state machine (ou services.py) publica via `publish_on_commit` após cada transição:

```python
publish_on_commit(RequisicaoEvent.AUTORIZADA, requisicao_id=req.id, actor_id=actor.id)
```

Notificações não podem falhar a transação principal — `publish_on_commit` garante isso disparando pós-commit.

**Subscriber em notifications**

```python
# apps/notifications/handlers.py
@subscribe(RequisicaoEvent)
def handle_requisicao_event(event: RequisicaoEvent, requisicao_id: int, actor_id: int):
    notificar(event, requisicao_id, actor_id)
```

**Routing interno**

`notificar()` encapsula uma routing table: `RequisicaoEvent → (get_destinatarios, build_payload, canais)`. Callers não conhecem destinatários, payload nem canal.

**Compatibilidade com ADR 0002**

O event bus (`publish_on_commit`) não é adequado para operações transacionais críticas — ADR 0002 registra isso e usa Port/Adapter para stock. Notificações não têm esse requisito: falha de notificação deve logar, não reverter. `publish_on_commit` é o mecanismo correto aqui.

## Regras derivadas

- `apps/requisitions/events.py` é a fonte de verdade para eventos de domínio de requisição.
- `apps/notifications/` importa de `apps/requisitions/events.py` — nunca o inverso.
- Novos eventos de notificação de requisição: adicionar ao enum em `events.py`, adicionar entrada na routing table em `notifications/services.py`. Nenhuma outra mudança em `requisitions`.
- Eventos de outros domínios (materiais, estoque): seguem o mesmo padrão — enum no domínio de origem, subscriber em `notifications`.
- `core/events.py` permanece infra técnica; não define eventos de domínio.
