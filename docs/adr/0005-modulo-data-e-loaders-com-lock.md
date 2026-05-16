# ADR 0005 — Módulo data.py e loaders com lock internos a contexts.py

## Status

Aceita.

## Contexto

`apps/requisitions/queries.py` mistura duas responsabilidades distintas:

1. **Loaders de leitura** — queries sem lock para retorno de objetos após operações.
2. **Loaders com lock** — `select_for_update(of=("self",))` para uso dentro de transações.
3. **Mutações** — `aplicar_quantidades_autorizacao`, `aplicar_itens_atendimento_completo`, `aplicar_itens_atendimento_parcial`, `bulk_create_itens`, `aplicar_edicao_rascunho`.

O nome `queries.py` implica somente leitura, tornando a presença de mutações inesperada. Mais crítico: dois loaders com lock são **idênticos** em implementação (`recarregar_para_autorizacao` e `recarregar_para_atendimento`), diferindo apenas no nome semântico — sem proteção técnica contra uso fora de um bloco `atomic()`.

Com a introdução de `contexts.py` (ADR 0004), os loaders com lock passaram a ser chamados exclusivamente de dentro de context managers que garantem `transaction.atomic()`. Manter esses loaders como funções públicas permite que qualquer caller os invoque fora de um contexto de transação — travando linhas sem rollback garantido.

## Decisão

### 1. Renomear `queries.py` para `data.py`

`data.py` nomeia honestamente o módulo como contendo acesso a dados (leituras e escritas), sem implicar somente leitura.

### 2. Loaders com lock migram para `contexts.py` como função privada

Os loaders `recarregar_para_autorizacao`, `recarregar_para_atendimento` e `carregar_rascunho_bloqueado` são removidos de `data.py`. Em `contexts.py`, uma única função privada substitui os dois loaders idênticos:

```python
# apps/requisitions/contexts.py

def _recarregar_com_lock(pk: int) -> Requisicao:
    return (
        Requisicao.objects
        .select_for_update(of=("self",))
        .select_related("criador", "beneficiario", "setor_beneficiario")
        .prefetch_related("itens__material__estoque", "eventos__usuario")
        .get(pk=pk)
    )
```

Cada `Contexto*` chama `_recarregar_com_lock` internamente. Callers externos não têm acesso a objetos bloqueados sem abrir um contexto.

### 3. Superfície pública de `data.py`

| Grupo | Funções |
|---|---|
| Read loaders (sem lock) | `recarregar_rascunho`, `recarregar_autorizado`, `recarregar_atendido`, `recarregar_detalhe`, `carregar_beneficiario_e_setor` |
| Item loader com lock | `carregar_itens_bloqueados` ¹ |
| Mutações de itens | `aplicar_quantidades_autorizacao`, `aplicar_itens_atendimento_completo`, `aplicar_itens_atendimento_parcial` |
| Mutações de requisição | `bulk_create_itens`, `aplicar_edicao_rascunho` |

¹ `carregar_itens_bloqueados` usa `select_for_update` mas é chamado por `services.py` **dentro** de um `Contexto*.abrir()` já aberto. Fica público pois o contexto garante o `atomic()` envolvente. Se no futuro for chamado fora de um contexto, deve migrar para `contexts.py`.

## Invariante protegida

> Objetos `Requisicao` com lock (`select_for_update`) só podem ser obtidos de dentro de um `Contexto*.abrir()`.

Esta invariante é garantida por construção: `_recarregar_com_lock` é privado a `contexts.py`, inacessível a callers externos.

## Regras derivadas

- `data.py` não deve conter `select_for_update` exceto em `carregar_itens_bloqueados`.
- Qualquer novo loader que precise de lock deve ser adicionado como função privada em `contexts.py`, não em `data.py`.
- Imports de `queries` em qualquer arquivo devem ser atualizados para `data` na migração.
- `contexts.py` importa de `data.py`; `data.py` não importa de `contexts.py` (sem ciclo).
- `services.py` importa de `data.py` (para read loaders e mutações) e de `contexts.py` (para context managers).
