# Plano — Issue #84: contexts.py + Contexto* + refatorar services.py

## Scope

**O que muda:**
- `apps/requisitions/contexts.py` criado (novo módulo)
- `apps/requisitions/data.py`: remove 3 loaders com lock
- `apps/requisitions/policies.py`: adiciona `pode_cancelar_requisicao`
- `apps/requisitions/services.py`: refatora 6 funções de transição + inline de 2 funções afetadas pela remoção dos loaders
- `tests/requisitions/test_contexts.py` (novo): testes de seam dos contextos

**O que NÃO muda:**
- Lógica de negócio (sem mudança comportamental)
- `retirar_requisicao` e `descartar_rascunho_nunca_enviado` — fora do escopo dos 4 contextos definidos
- Contrato HTTP / serializers / views / OpenAPI

## Files touched

| Arquivo | Mudança |
|---|---|
| `apps/requisitions/contexts.py` | Criação: `_recarregar_com_lock`, 4 `Contexto*` |
| `apps/requisitions/data.py` | Remove `recarregar_para_autorizacao`, `recarregar_para_atendimento`, `carregar_rascunho_bloqueado` |
| `apps/requisitions/policies.py` | Adiciona `pode_cancelar_requisicao` |
| `apps/requisitions/services.py` | Refatora `enviar_para_autorizacao`, `autorizar_requisicao`, `recusar_requisicao`, `cancelar_requisicao`, `atender_requisicao_completa`, `atender_requisicao_com_itens`; inline loader em `retornar_para_rascunho` e `atualizar_rascunho_requisicao` |
| `tests/requisitions/test_contexts.py` | Novo: testes de seam dos 4 contextos |

## Contextos definidos (ADR 0004 + ADR 0005)

| Classe | Loader | Policy | Extras |
|---|---|---|---|
| `ContextoEnvio` | `_recarregar_com_lock` | `pode_manipular_pre_autorizacao` | `is_primeiro_envio: bool` |
| `ContextoAutorizacao` | `_recarregar_com_lock` | `pode_autorizar_requisicao` | — |
| `ContextoCancelamento` | `_recarregar_com_lock` | `pode_cancelar_requisicao` (nova) | `requer_liberacao_estoque: bool` |
| `ContextoAtendimento` | `_recarregar_com_lock` | `pode_atender_requisicao` | — |

## `pode_cancelar_requisicao` (nova policy)

Despacha para a policy correta com base no status carregado:
- `AUTORIZADA` → `pode_cancelar_autorizada(user, req)`
- Demais → `pode_manipular_pre_autorizacao(user, req)`

Isso permite que `ContextoCancelamento.abrir()` faça um único check antes de `yield`.

## Loaders removidos de data.py

- `recarregar_para_autorizacao` → substituído por `_recarregar_com_lock` em `contexts.py`
- `recarregar_para_atendimento` → substituído por `_recarregar_com_lock` em `contexts.py`
- `carregar_rascunho_bloqueado` → inline em `atualizar_rascunho_requisicao` (mesma query + NotFound handling)

`retornar_para_rascunho` usava `recarregar_para_atendimento` — será atualizado com inline `select_for_update`.

## Test strategy

`tests/requisitions/test_contexts.py` cobre, para cada contexto:
- Permission denied: ator sem permissão → `PermissionDenied`
- Status inválido: objeto no estado errado → `DomainError` / `DomainConflict` via `apply_transition`
- Happy path: contexto abre, atributos extras corretos

Testes de serviços existentes em `test_services.py` permanecem como regressão.

## Invariants preserved

- `select_for_update` apenas dentro de `transaction.atomic()` (garantido pelos context managers)
- `_recarregar_com_lock` privado: callers externos não acessam objeto bloqueado sem contexto
- `data.py` sem `select_for_update` exceto `carregar_itens_bloqueados`
- Lógica de negócio permanece em `services.py`
- `contexts.py` importa de `models.py` e `policies.py`; nunca de `services.py` nem de `data.py`

## Risks

- Nenhuma mudança de comportamento — risco de regressão baixo coberto pela suíte existente
- `cancelar_requisicao` redireciona sub-funções via `ctx.requer_liberacao_estoque` — validar path feliz de ambos os branches nos testes novos
