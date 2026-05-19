# Domain Docs

How engineering skills should consume this repo's domain documentation when exploring codebase.

## Layout

This repo is **single-context**.

Read:

- root `CONTEXT.md`
- root `docs/adr/`
- `docs/design-acesso-rapido/` first for fast operational guidance
- `docs/design-acesso-ocasional/` only when quick docs do not resolve question, ambiguity exists, or task needs deeper domain detail

If some file is absent in future, proceed silently. Do not invent missing doc requirements mid-task.

## Repo-specific consumer rules

- Start with `docs/design-acesso-rapido/`
- Use `docs/design-acesso-rapido/frontend-arquitetura-piloto.md` for pilot frontend work
- Use `docs/design-acesso-rapido/api-contracts.md` for DRF contract work
- Use `docs/design-acesso-rapido/matriz-permissoes.md` for papel/escopo questions
- Use `docs/design-acesso-rapido/matriz-invariantes.md` and `estado-transicoes-requisicao.md` for requisition/stock invariants
- Use `docs/backlog/backlog-tecnico-piloto.md` for phase, gate, and delivery scope

## Use glossary vocabulary

When naming domain concepts, use terms from `CONTEXT.md`. Do not drift to synonyms that glossary rejects.

Important current distinctions:

- `Auxiliar de setor` is not authorizer
- `Descartar rascunho` is not same as `Cancelar requisição`
- Pilot currently uses one `Papel operacional principal` per user

## ADR conflicts

If proposal contradicts ADR, surface conflict explicitly instead of silently overriding it.
