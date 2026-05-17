# Plan: #83 — test(requisitions): cobertura de service para CRUD de rascunho e atendimento

## Scope

Adicionar testes diretos de service em `tests/requisitions/test_services.py`.
Zero mudança em código de produção.

## Files touched

- `tests/requisitions/test_services.py` — nova classe `TestRascunhoCRUDEAtendimentoService` appended ao final

## Test strategy

Nova classe `@pytest.mark.django_db(transaction=True)` com helpers próprios (códigos de material no
range `099.001.XXX` para evitar colisão com testes existentes).

### `criar_rascunho_requisicao`

| Caso | Expectativa |
|---|---|
| Happy path | status=RASCUNHO, itens criados |
| Material inativo | `DomainConflict` |
| Quantidade > saldo | `DomainConflict` |
| Itens vazios | `ValidationError` |

### `atualizar_rascunho_requisicao`

| Caso | Expectativa |
|---|---|
| Happy path | beneficiário e itens substituídos |
| Status ≠ RASCUNHO | `DomainConflict` |
| Ator = superuser (vê mas não manipula) | `PermissionDenied` |

Nota: para RASCUNHO, `pode_visualizar_requisicao` só permite criador — qualquer outro usuário
não-criador recebe `NotFound` antes de chegar em `PermissionDenied`. O caso `PermissionDenied`
é atingido via superuser: passa `pode_visualizar_requisicao` mas falha `usuario_operacional_ativo`.

### `descartar_rascunho_nunca_enviado`

| Caso | Expectativa |
|---|---|
| Happy path | requisição e itens deletados do DB |
| Rascunho com `numero_publico` (formalizado) | `DomainConflict` |
| Ator ≠ criador | `PermissionDenied` |

### `atender_requisicao_com_itens` (via `atender_requisicao`)

| Caso | Expectativa |
|---|---|
| Entrega acima do autorizado | `DomainConflict` |

Validação ocorre antes de qualquer operação de stock — não necessita mock de StockPort.

## Invariants preserved

- Nenhum arquivo de produção modificado
- ADR 0007: toda regra de domínio coberta em test_services antes de test_api

## Risks

Nenhum — somente testes, zero risco de regressão em código de produção.
