# ADR 0007 — Pirâmide de testes: regra de cobertura por camada

## Status

Aceita. Implementação pendente (ver seção "Débito atual").

## Contexto

`tests/requisitions/test_services.py` (51 testes) e `tests/requisitions/test_api.py` (92 testes) coexistem, mas a cobertura está concentrada na camada errada para regras de domínio.

Três service functions têm lógica de validação e domínio sem nenhum teste direto de service:

| Service function | Regras sem cobertura de service |
|---|---|
| `criar_rascunho_requisicao` | material inativo, quantidade > saldo, rascunho sem itens |
| `atualizar_rascunho_requisicao` | status inválido para edição, permissão contextual, beneficiário inativo |
| `descartar_rascunho_nunca_enviado` | rascunho já enviado (formalizado), permissão |
| `atender_requisicao` | entrega acima do autorizado |

Essas regras são testadas exclusivamente via HTTP (`test_api.py`), o que significa:

- Falhas de domínio são diagnosticadas com mais ruído (foi a view? o serializer? o service? o validator?)
- Testes de domínio são mais lentos que o necessário (stack HTTP completo para verificar uma invariante de negócio)
- A interface do service não é o seam de teste — o endpoint HTTP é

## Decisão

### Regra de cobertura por camada

**Toda regra de domínio deve ter cobertura em `test_services.py` (ou equivalente de service) antes de qualquer cobertura em `test_api.py`.**

O que pertence a cada camada:

| Camada | O que testar |
|---|---|
| `test_services.py` | Regras de domínio (happy path, permissão negada, violação de domínio, concorrência) |
| `test_api.py` | Contrato HTTP (status codes, envelope de erro, autenticação, escopo de visibilidade) |

`test_api.py` não é proibido de testar regras de domínio — mas não deve ser a única cobertura delas.

### Débito atual a implementar

Adicionar testes de service para os gaps listados acima. Casos mínimos por função:

**`criar_rascunho_requisicao`**
- Material inativo → `DomainConflict` ou `ValidationError`
- Quantidade solicitada > saldo disponível → erro
- Lista de itens vazia → erro
- Happy path: requisição criada com status `RASCUNHO`

**`atualizar_rascunho_requisicao`**
- Requisição fora de status rascunho → erro de domínio
- Ator sem permissão de manipulação → `PermissionDenied`
- Happy path: beneficiário e itens substituídos corretamente

**`descartar_rascunho_nunca_enviado`**
- Rascunho já enviado (formalizado) → erro de domínio
- Ator sem permissão → `PermissionDenied`
- Happy path: requisição e itens deletados

**`atender_requisicao`**
- Entrega acima do autorizado → erro de domínio

## Regras derivadas

- Toda nova regra de domínio ganha teste de service primeiro. Teste de API para a mesma regra é opcional (cobre contrato HTTP adicional).
- Ao adicionar um endpoint novo, a checklist de PR deve incluir: "existe teste de service para cada regra de domínio do service chamado?"
- Testes de concorrência (`select_for_update`, race conditions) pertencem exclusivamente a `test_services.py` — nunca via HTTP.
- Testes de escopo e visibilidade (quem vê o quê) pertencem exclusivamente a `test_api.py`.
