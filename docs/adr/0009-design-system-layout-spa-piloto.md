# ADR 0009 — Design system e layout base da SPA do piloto

## Status

Aceita.

## Contexto

Após o reset neutro do frontend do piloto, a issue #29 precisava impedir que a PR #30 recriasse decisões visuais antigas ou inventasse shell, navegação e primitives sem contrato. A SPA continua sendo uma ferramenta operacional do Almoxarifado do SAEP, não uma landing page nem um dashboard genérico.

## Decisão

A PR #30 deve materializar `shadcn/ui` + `Radix UI` de forma incremental, com uma primeira leva mínima e fechada de primitives: `Button`, `Input`, `Label`, `Alert`, `Separator`, `Sheet` e `Card`. Essa lista cobre login, shell autenticado, navegação responsiva e mensagens de erro/negação de permissão sem antecipar componentes de fluxos ainda inexistentes. `DropdownMenu`, `Dialog`, `Tabs`, `Table`, `Badge` e `Toast` ficam fora da PR #30 até haver uso funcional concreto. `lucide-react` pode ser adicionada como dependência visual mínima, com ícones apenas como apoio ao texto ou em controles icon-only com nome acessível.

O shell autenticado deve ser desktop-first, mas já responsivo: sidebar persistente e topo compacto no desktop; navegação recolhida em menu/drawer no mobile. `/login` fica fora do shell autenticado, com layout próprio, marca `SAEP`, nome funcional `WMS Almoxarifado`, formulário compacto e erro visível.

A navegação principal deve esconder áreas que não pertencem ao papel operacional do usuário, enquanto acessos diretos por URL devem renderizar negativa de permissão clara. `/` não terá dashboard próprio na PR #30: redireciona conforme sessão e papel. `Nova requisição` aparece para todos os papéis operacionais ativos como ação primária/rota protegida placeholder, mas não como destino automático pós-login.

A PR #30 deve estabelecer um baseline pragmático de acessibilidade alinhado a WCAG AA para autenticação e shell: foco visível em todos os controles interativos, navegação essencial por teclado, `Label` explícito para inputs, mensagens de erro associadas ao campo quando aplicável, contraste mínimo AA, alvos de clique/toque confortáveis, ícones isolados sempre com nome acessível, estados de foco/hover/disabled/erro distinguíveis sem depender apenas de cor e nenhuma informação transmitida exclusivamente por cor. A PR #30 não exige auditoria completa de acessibilidade, mas esses contratos devem ser cobertos por smoke/unit tests onde fizer sentido.

O contrato de testes da PR #30 deve ter duas camadas. A camada principal é Vitest, cobrindo a matriz de regras: redirect por sessão e papel, login fora do shell, home por papel, papel desconhecido, menu por papel, `Nova requisição` para papéis operacionais, acesso direto negado, logout, erro de login, sessão expirada e erro de bootstrap. A camada Playwright é smoke, não matriz completa: um caminho feliz com login real, shell, navegação mínima e logout; e um caminho negativo de acesso direto proibido renderizando 403 amigável. Worklists ficam fora dos testes da PR #30. Esconder menu é UX; proteção de rota continua sendo requisito de segurança e produto.

O shell da PR #30 deve ser stateless quanto a preferências visuais. No mobile, o menu usa apenas estado local e fecha ao navegar, ao fazer logout ou quando a rota muda. No desktop, a sidebar permanece sempre visível, sem colapso. Persistência em `localStorage` ou `sessionStorage` fica fora da PR #30 e só deve ser reaberta por requisito claro de produtividade, problema validado de espaço horizontal ou decisão formal posterior de layout.

A PR #30 não deve introduzir sistema global de toast. Erro de login pertence ao formulário; erro de bootstrap deve ser um estado de página retryable; erro de logout deve ficar visível no shell ou na área de conta. Feedback transitório global fica para issue futura, quando houver eventos assíncronos não bloqueantes que justifiquem provider, fila, duração, acessibilidade e testes próprios. Primitives mínimas como `FormError`, `InlineAlert` e `RetryableState` são aceitáveis se permanecerem contextuais.

O `components.json` do shadcn deve ser versionado já alinhado à taxonomia do repositório: primitives em `frontend/src/shared/ui` e utilitários em `frontend/src/shared/lib`. A PR #30 não deve criar `components/ui` nem `lib/utils` paralelos, porque a ferramenta não deve redefinir as fronteiras documentadas do projeto.

Componentes genéricos reutilizáveis ficam em `shared/ui`. Componentes compostos e específicos do shell/auth da PR #30 não devem ser promovidos para `shared/ui`; devem permanecer no módulo/app layer correspondente até demonstrarem reutilização real. `Alert` deve ser usado para feedback contextual persistente de erro, negação de permissão e indisponibilidade. `Sheet` deve ser usado apenas para a navegação mobile do shell; formulários, detalhes, confirmação e fluxos operacionais em `Sheet` ficam fora do escopo da PR #30.

## Consequências

- A PR #30 prova autenticação, shell, papel, navegação e guards sem implementar worklists, tabelas, wizard, notificações, PWA, analytics ou fluxos de requisição.
- A UI deve manter tom institucional, sóbrio e operacional, com tema claro, alto contraste, poucos acentos e densidade moderada.
- `WMS-SAEP` permanece nome técnico do projeto; a interface operacional deve expor `SAEP` e `WMS Almoxarifado`.
