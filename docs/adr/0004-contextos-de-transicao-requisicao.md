# ADR 0004 — Contextos de transição de requisição

## Status

Aceita.

## Contexto

`apps/requisitions/services.py` expõe uma função nomeada por operação de domínio (`enviar_para_autorizacao`, `autorizar_requisicao`, `recusar_requisicao`, `cancelar_requisicao`, `atender_requisicao`). Cada função reimplementa o mesmo padrão de pré-voo de forma inconsistente:

1. `transaction.atomic()` — presente em todas, mas `recusar_requisicao` valida `motivo` fora do bloco.
2. Reload com lock — cada função chama um `queries.recarregar_*` diferente sem convenção explícita.
3. Permission check — alguns via `queries`, outros chamam policy diretamente.
4. `apply_transition()` — consistente.

O resultado: quatro variações do mesmo padrão, nenhuma testável de forma isolada, e sem contrato claro para novas transições seguirem.

## Decisão

Introduzir o módulo `apps/requisitions/contexts.py` com uma classe de contexto por operação de domínio. Cada classe é um context manager que encapsula exclusivamente: `transaction.atomic()`, reload com lock, e permission check. A lógica específica da operação permanece em `services.py`.

### Interface padrão

```python
@classmethod
@contextmanager
def abrir(cls, requisicao: Requisicao, ator: User) -> Generator[Self, None, None]:
    with transaction.atomic():
        req = queries.recarregar_*(requisicao)  # loader específico da operação
        if not <policy>(ator, req):
            raise PermissionDenied(...)
        yield cls(requisicao=req, ator=ator, **kwargs_específicos)
```

### Contextos definidos

| Classe | Loader | Policy | Atributos extras |
|---|---|---|---|
| `ContextoEnvio` | `recarregar_para_autorizacao` | `pode_manipular_pre_autorizacao` | `is_primeiro_envio: bool` |
| `ContextoAutorizacao` | `recarregar_para_autorizacao` | `pode_autorizar_requisicao` | — |
| `ContextoCancelamento` | `recarregar_para_atendimento` | `pode_cancelar_requisicao` | `requer_liberacao_estoque: bool` |
| `ContextoAtendimento` | `recarregar_para_atendimento` | `pode_atender_requisicao` | — |

Atributos extras expõem fatos observáveis no momento do carregamento que o service precisa para decidir ramificações internas (ex: `is_primeiro_envio` determina `"enviar"` vs `"reenviar"`; `requer_liberacao_estoque` determina se o stock port é acionado no cancelamento).

### Services.py após a mudança

```python
def autorizar_requisicao(*, requisicao, ator, itens, stock=None):
    if stock is None:
        stock = _get_default_stock()
    with ContextoAutorizacao.abrir(requisicao, ator) as ctx:
        itens_requisicao = queries.carregar_itens_bloqueados(ctx.requisicao)
        itens_por_id = validation.validar_itens_autorizacao(itens_requisicao, itens)
        queries.aplicar_quantidades_autorizacao(itens_requisicao, itens_por_id)
        transicao = "autorizar_parcial" if any(...) else "autorizar_total"
        apply_transition(ctx.requisicao, transicao, ctx.ator, payload={...})
        stock.aplicar_reservas_autorizacao(ctx.requisicao, itens_autorizados)
    return queries.recarregar_autorizado(requisicao.pk)
```

### Seam de teste

O contexto é testável pela sua própria interface, sem passar por HTTP:

```python
def test_contexto_autorizacao_rejeita_ator_sem_permissao(db):
    with pytest.raises(PermissionDenied):
        with ContextoAutorizacao.abrir(req, ator_sem_permissao):
            pass

def test_contexto_autorizacao_rejeita_status_invalido(db):
    with pytest.raises(DomainError):
        with ContextoAutorizacao.abrir(req_em_rascunho, ator_valido):
            pass
```

## Regras derivadas

- Toda nova transição de requisição deve ter um `Contexto*` correspondente em `contexts.py`.
- O contexto encapsula **apenas**: `atomic()`, reload com lock, permission check, e atributos observáveis no carregamento.
- Lógica de negócio específica da operação (validação de itens, stock, decisão de transição) permanece em `services.py`.
- Nenhuma função de `services.py` deve abrir `transaction.atomic()` diretamente — o contexto é o único ponto de abertura.
- Atributos extras no contexto devem ser fatos observáveis do estado carregado, não decisões de negócio.
- `contexts.py` importa de `queries.py` e `policies.py`; não importa de `services.py` (sem ciclo).
