# Débito Técnico: Write-once DB-level para campos de auditoria de retirada

## Status
Aberto — inalterado pelo reset do frontend.

## Problema
`data_retirada` e `retirante_fisico` em `apps/requisitions/models.py` são protegidos apenas no nível ORM:
- `Requisicao.save()` verifica se campo já preenchido antes de sobrescrever.
- `RequisicaoQuerySet.update()` bloqueia kwargs com esses campos quando já preenchidos via `exists()` + `update()`.

Proteção ORM não cobre:
- SQL direto (`cursor.execute`)
- bibliotecas que bypassam o ORM
- janela de corrida no padrão `exists()` -> `update()` sob concorrência

## Correção esperada
Trigger PostgreSQL `BEFORE UPDATE` na tabela `requisitions_requisicao` para tornar `data_retirada` e `retirante_fisico` write-once após preenchimento.

## Bloqueio atual
Migrations são gitignored (`apps/**/migrations/*.py`). A migration com trigger não seria versionada/aplicada em CI. Resolver antes de implementar: decidir se a migration inicial deve incluir o trigger ou se o gitignore deve ser ajustado para migrations de infra (triggers, funções).

## Referências
- `apps/requisitions/models.py`: `RequisicaoQuerySet` e `Requisicao.save()`
- guideline: proteger campos snapshot/históricos contra alteração após criação
- guideline: não depender só de `save()`, `clean()` ou validação de serializer para invariantes críticos