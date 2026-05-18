# ADR 0008 — Reset neutro do frontend do piloto

## Status

Aceita.

## Contexto

A issue #27 descartou a UI de produto atual da SPA. A issue #28 formaliza o reset neutro: remover a superfície de produto sem perder a infraestrutura técnica já útil para o piloto.

O risco principal é agentes futuros confundirem código antigo com direção de produto vigente e reintroduzirem rotas, telas, layout ou fluxos descartados antes da decisão visual da issue #29.

## Decisão

O frontend do piloto entra em estado neutro.

Preservar:

- diretório `frontend/`;
- Vite, React e TypeScript;
- TanStack Router e TanStack Query;
- client OpenAPI tipado e geração de schema;
- smoke tests e integração operacional via `Makefile`;
- contrato técnico de sessão Django + CSRF.

Remover do contrato vigente:

- comportamento de produto antigo nas rotas preservadas;
- shell autenticado definitivo;
- worklists operacionais;
- telas de detalhe, criação, autorização e atendimento;
- decisões visuais, layout e navegação de produto anteriores.

As rotas públicas documentadas permanecem acessíveis no reset, mas renderizam apenas título e a mensagem `Interface do piloto em reconstrucao.`. Até a issue #29 fechar design system e layout base, qualquer rota mantida ou criada deve ser neutra, técnica e mínima. A PR #30/auth-shell fica bloqueada por essa decisão.

## Consequências

- a infraestrutura da SPA continua reaproveitável;
- o produto visual deixa de carregar decisões descartadas;
- novas fatias de frontend devem partir do reset, não do produto antigo;
- a próxima decisão obrigatória antes da PR #30/auth-shell é a issue #29.

## Regras derivadas

- Não ressuscitar telas, rotas ou fluxos antigos sem ADR ou issue explícita posterior.
- Não tratar código removido como fonte de verdade de produto.
- Documentar rotas atuais como contrato neutro, não como mapa final da SPA.
- Se houver conflito entre memória/código antigo e esta ADR, esta ADR prevalece.
