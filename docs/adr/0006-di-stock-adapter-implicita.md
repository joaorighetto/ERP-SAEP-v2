# ADR 0006 — DI implícita do StockAdapter via `_get_default_stock()`

## Status

Aceita.

## Contexto

`apps/requisitions/services.py` expõe três funções que interagem com estoque (`autorizar_requisicao`, `cancelar_requisicao`, `retirar_requisicao`). Cada uma aceita `stock: StockPort | None = None`. Quando `None`, a dependência é resolvida por `_get_default_stock()`:

```python
def _get_default_stock() -> StockPort:
    from apps.stock.adapters import StockAdapter
    return StockAdapter()
```

O import é feito dentro da função (não no topo do módulo) para evitar circular import entre `requisitions` e `stock`.

A alternativa avaliada foi tornar `stock` obrigatório em todas as assinaturas, forçando callers (views, testes de integração) a passar o adapter explicitamente.

## Decisão

Manter o padrão atual: `stock: StockPort | None = None` + `_get_default_stock()`.

### Por que não foi feita a mudança

**Um só adapter real = seam hipotético.** O princípio aplicado aqui é: um seam se justifica quando existem dois ou mais implementações concretas com necessidades distintas. Hoje existe apenas `StockAdapter`. Tornar o parâmetro obrigatório adicionaria ruído em views e nos ~44 testes de integração sem nenhum ganho imediato.

**Testes de integração usam o adapter real propositalmente.** Os testes que chamam `autorizar_requisicao` sem `stock=` verificam o efeito colateral no saldo físico (`saldo_reservado`, `saldo_fisico`). Forçar o stub nesses testes perderia cobertura real.

**O seam já é acessível.** `StockPort` (Protocol) está definido em `ports.py`, o parâmetro existe nas assinaturas, e `TestPortAdapterStock` já usa `StubStockPort` para testar o contrato do port isoladamente. A interface de substituição funciona sem mudança de produção.

**O import dinâmico é aceitável.** É um padrão estabelecido no Django para evitar circular imports em tempo de módulo. Não causa confusão operacional.

## Regras derivadas

- Não tornar `stock` obrigatório enquanto houver apenas um adapter real.
- Se um segundo adapter concreto for necessário (ex: `NullStockAdapter` para ambientes sem estoque, adapter alternativo para testes E2E), revisitar esta ADR e migrar para DI explícita.
- `_get_default_stock()` deve continuar usando import dinâmico para evitar circular import.
- Novos métodos no `StockPort` devem ser implementados em `StockAdapter` e em `StubStockPort` (em `tests/requisitions/helpers.py`) simultaneamente.
