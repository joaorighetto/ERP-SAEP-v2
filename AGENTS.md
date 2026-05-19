# AGENTS.md

## Habilidades dos agentes

### Rastreador de issues

As issues deste repositório ficam no GitHub Issues. Use `gh`. Veja `docs/agents/issue-tracker.md`.

### Labels de triagem

O repositório usa labels padrão de triagem: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. Veja `docs/agents/triage-labels.md`.

### Documentação de domínio

O repositório é de contexto único. Leia primeiro o `CONTEXT.md` na raiz, `docs/adr/` na raiz e depois `docs/design-acesso-rapido/`; consulte `docs/design-acesso-ocasional/` quando precisar de mais profundidade. Veja `docs/agents/domain.md`.

## Preferências de ferramentas MCP

- Sempre use o Serena MCP para navegação e edição de código (`find_symbol`, `replace_content`) em vez de Read/Edit neste codebase.
- Sempre consulte o Context7 MCP antes de implementar algo contra bibliotecas/frameworks de terceiros (Django, DRF, TanStack, React etc.).
- Prefira ferramentas MCP a Read/Bash genéricos ao explorar a estrutura do código — Serena é eficiente em tokens.
- Para revisões de código, delegue ao agente `senior-code-reviewer` e produza achados estruturados.

## Projeto

WMS auxiliar para o **SAEP — Serviço de Água e Esgoto de Pirassununga**, autarquia municipal. O projeto segue **backend/API-first** em **Django 6 + Django REST Framework (DRF)** e a frente ativa de frontend do piloto volta a ser **server-rendered no Django**.

O reset atual abandona a fundação SPA anterior. A nova direção do piloto é:

- Django templates como superfície principal;
- `django-htmx` para interações incrementais;
- Tailwind CSS para styling;
- Alpine.js apenas onde HTMX não cobrir a interação com simplicidade suficiente.

Não ressuscite `frontend/`, Vite, React, TanStack ou fluxos da SPA antiga sem decisão explícita posterior.

## Estratégia de leitura da documentação

Para economizar tokens e manter os agentes focados, a documentação de design do projeto está dividida por frequência de uso:

- `docs/design-acesso-rapido/`: sínteses operacionais. Deve ser a primeira fonte consultada por agentes de IA.
- `docs/design-acesso-ocasional/`: documentação completa. Deve ser consultada apenas quando a síntese rápida não resolver a dúvida, quando houver ambiguidade ou quando a tarefa depender de detalhe de domínio.
- `docs/code-review-guidelines.md` e `.coderabbit.yaml`: orientam o comportamento de revisões de código.

### IDs do Context7 para consulta rápida:

- Django 6: `/django/django/6_0a1`
- DRF: `/websites/django-rest-framework`
- django-htmx: `/adamchainz/django-htmx`
- Tailwind CSS: `/tailwindlabs/tailwindcss.com`
- Alpine.js: `/websites/alpinejs_dev`

### Quando consultar o Context7 (gatilhos):

| Área alterada | Consultar |
|---|---|
| `Model`, fields, constraints, indexes | Django Models, Fields, Meta, Constraints |
| Relacionamentos (`FK`, `M2M`, `O2O`) | Django ForeignKey, related_name, on_delete |
| Transações, locks, saldo | Django `transaction.atomic()`, `select_for_update()` |
| DRF Serializer | Serializers, ModelSerializer, validação, representação |
| ViewSet / APIView | DRF ViewSets, Generic Views, Mixins, Routers |
| Autorização | DRF Permissions + `policies.py` do projeto |
| Filtros, busca, ordenação | DRF Filtering, QuerySet API, lookup expressions |
| Testes | Django TestCase, pytest-django, DRF APIClient |
| Frontend do piloto server-rendered | `docs/design-acesso-rapido/frontend-arquitetura-piloto.md` + IDs acima |
| Management commands, signals, admin, settings | Documentação específica da área |

**Nunca**: implementar Django/DRF sem consultar Context7. Nunca assumir APIs sem confirmar versão atual. Nunca misturar versões de Django/DRF/libs. Nunca iniciar o frontend do piloto sem confirmar o contrato documentado vigente.


## Ambiente de desenvolvimento efêmero

Durante a fase inicial, o ambiente local é descartável.

- o banco local pode ser apagado e recriado;
- o fluxo padrão é resetar banco -> aplicar migrations -> carregar dados mínimos (quando existirem);
- migrations locais são não versionadas e ignoradas pelo `.gitignore`.
- `rtk make init` deve ser usado no setup inicial do projeto para criar `.venv` e instalar dependências.
- `rtk make test` executa a suíte com `DJANGO_SETTINGS_MODULE=config.settings.test` e opções econômicas/seguras de pytest: `-q -ra --tb=short --strict-markers --disable-warnings`;
- Para execução manual equivalente, use `DJANGO_SETTINGS_MODULE=config.settings.test pytest -q -ra --tb=short --strict-markers --disable-warnings`;
- `rtk make run` sobe o servidor de desenvolvimento Django na porta padrão;
- os entrypoints do frontend server-rendered serão definidos junto com a nova infraestrutura; não reutilize os comandos `frontend-*` da SPA removida;
- neste momento do projeto, toda edição de `models`/schema deve ser seguida de `rtk make setup`, para não depender de gestão manual de migrations.
- migrations de apps devem ser tratadas como artefato efêmero: antes de testar ou concluir uma implementação que altere schema, apagar e recriar as migrations locais do zero, simulando uma primeira execução limpa do app.
- confeccionar novos arquivos de migration não faz parte da entrega normal do trabalho neste contexto efêmero.
- a fonte de verdade para mudanças estruturais são `models`, constraints, índices, regras de domínio e testes; migrations locais servem apenas para materializar o banco local.
- tarefas sem mudança estrutural podem seguir fluxo incremental; reset completo é obrigatório apenas para mudanças de schema/model ou quando o ambiente local estiver inconsistente.
- todos os comandos shell e `make` devem ser chamados com prefixo `rtk`, usando `rtk proxy` apenas quando `rtk` não suportar a forma necessária.

## Guardrails Para o Projeto

### Faça

- Declare em todo endpoint: autenticação, autorização, entrada, saída, status HTTP, envelope de erro, paginação/filtros e schema OpenAPI.
- Siga `docs/design-acesso-rapido/api-contracts.md` como contrato canônico para endpoints DRF.
- Siga `docs/design-acesso-rapido/frontend-arquitetura-piloto.md` como contrato canônico para a arquitetura do frontend do piloto.
- Centralize regras de autorização contextual em `policies.py` ou equivalente.
- Faça views e services chamarem a mesma política de autorização.
- Valide perfil e escopo do objeto no service para toda escrita.
- Mantenha regras de negócio em services.
- Use uma máquina de estados declarativa, com tabela de transições e uma única função aplicadora.
- Mantenha uma única fonte de verdade para aprovação, status, saldo, entrega e auditoria.
- Proteja campos snapshot/históricos contra alteração após criação.
- Reforce invariantes críticos com constraints, triggers, managers ou testes de bypass.
- Use `transaction.atomic()`, `select_for_update()` e ordem determinística de locks em mutações de saldo ou ledger.
- Rode testes PostgreSQL na CI para locking, constraints, índices parciais e concorrência.
- Gere e compare o schema OpenAPI na CI.
- Trate o OpenAPI exportado como contrato vivo entre backend e frontend, mesmo no frontend server-rendered.
- Use `publish_on_commit()` para side effects pós-transação.
- Adicione teste de regressão para todo bug corrigido.
- Cubra regra crítica com caminho feliz, permissão negada, violação de domínio e contrato de erro.

### Não Faça

- Não deixe contrato HTTP para “arrumar depois”.
- Não exponha endpoint sem contrato explícito de entrada, saída, erros e permissões.
- Não trate o admin do Django como substituto da interface operacional do piloto.
- Não duplique regra de autorização entre view, service e serializer.
- Não confie só em `permission_classes` quando a regra depende do objeto ou departamento.
- Não coloque regra de negócio em views, serializers, admin actions, signals ou management commands.
- Não crie caminhos paralelos que gravem o mesmo estado de formas diferentes.
- Não implemente transições de status com `if/elif` espalhado por várias funções.
- Não trate código existente como fonte de verdade quando ele conflitar com documentação ou invariantes.
- Não deixe campo histórico/snapshot ser recalculado ou atualizado depois da criação.
- Não dependa só de `save()`, `clean()` ou validação de serializer para invariantes críticos.
- Não assuma que testes em SQLite provam comportamento de PostgreSQL.
- Não altere saldo, ledger ou registros auditáveis sem transação e lock.
- Não faça notificações ou side effects decidirem o sucesso da operação principal.
- Não aceite mudança de contrato sem atualizar OpenAPI, testes e documentação.
- Não implemente frontend do piloto em desacordo com o ADR macro e o guia operacional do frontend.
- Não corrija bug sem adicionar teste que falharia antes da correção.

## Fluxo de trabalho Git

- **Nunca faça commit diretamente na main** — sempre crie uma branch de feature primeiro.
- Confirme a branch atual antes de qualquer operação de commit.
- Ao abrir PRs em repositórios forkados, aponte para o remote upstream, não para origin.
- Nomes de branch: `feat/{desc}`, `fix/{desc}`, `refactor/{desc}`, `test/{desc}`, `docs/{desc}`, `chore/{desc}`.
- Commits devem ser pequenos, coesos e reversíveis — uma unidade lógica por commit.

## Fluxo GitHub

- `main` sempre estável — nenhum commit direto
- Antes de implementar crie branches: `feat/{descricao-curta}`, `fix/{descricao-curta}`, `chore/{descricao-curta}`, `docs/{descricao-curta}`, `refactor/{descricao-curta}`, `test/{descricao-curta}`
- nomes de branch devem ser curtos, sem acentos, sem espaços e refletir uma única unidade de mudança
- evitar branches e PRs com escopo amplo demais; dividir trabalho extenso em fatias auditáveis
- Sempre que publicar um PR, preencha o `.github/pull_request_template.md` detalhadamente
- Quando houver divergência com `.serena/memories` ou ambiguidade de contrato, o PR deve explicitar a decisão tomada

### Commits pequenos e incrementais

Ao implementar uma tarefa, prefira fazer **commits pequenos, coesos e revisáveis** em vez de um único commit grande no final.

Diretrizes:

- Faça commits por unidade lógica de mudança.
- Cada commit deve deixar o projeto em um estado consistente.
- Evite misturar refactors, mudanças de modelo, migrations, testes e ajustes de documentação no mesmo commit quando puder separá-los.
- Rode os checks relevantes antes de cada commit ou, no mínimo, antes de finalizar a sequência.
- Use mensagens de commit descritivas, explicando o que mudou.
- Commits no padrão Conventional Commits (`feat:`, `fix:`, `test:`, `refactor:`, `chore:`, `docs:`)

Exemplos de bons commits:

feat(materials): add Material model
feat(stock): add EstoqueMaterial model
test(materials): cover Material validation
test(stock): cover available quantity calculation
docs: update pilot data modeling notes


## Fluxo de revisão de código

- Para revisões de código, **delegue ao agente `senior-code-reviewer`** e produza achados estruturados com níveis de severidade (Critical/Major/Minor).
- Sempre inclua **referências a números de linha** e verifique que correspondem ao código atual.
- Entregue **revisões completas** — não truncar. Se forem longas, salve os achados em `docs/code-reviews/<branch-or-pr>-<date>.md` com seções estruturadas.
- Revisões (automáticas ou manuais) devem seguir `docs/code-review-guidelines.md`.
- Em caso de conflito com sugestões genéricas, prevalecem os invariantes arquiteturais e de domínio documentados no projeto.


## Execução de testes

- **Sempre execute a suíte backend com `rtk make test` limpo, sem redirecionamentos, pipes, `tail`, `head`, `grep` ou truncamento de saída.** Quando houver falha, use o caminho `[full output: ...]` emitido pelo Tee System para inspecionar a saída bruta completa sem reexecutar o comando.
- Rode a suíte completa de testes após qualquer refactor e confirme a contagem de testes passados antes de commitar.
- Ao depurar falhas de teste, capture o traceback completo antes de tentar corrigir.
- Para testes Django: `rtk make test` (usa `DJANGO_SETTINGS_MODULE=config.settings.test` com opções seguras do pytest).
- Para testes do frontend server-rendered, defina checks no mesmo PR que introduzir a nova infraestrutura. Não ressuscite Vitest/Playwright da SPA sem nova decisão explícita.
