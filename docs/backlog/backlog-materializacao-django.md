# Backlog Técnico — Materialização Mínima Django

Este documento reúne apenas as tarefas técnicas necessárias para transformar o repositório em um projeto Django inicializável antes do início do backlog funcional do piloto.

Para o backlog funcional do piloto inicial, consultar `docs/backlog/backlog-tecnico-piloto.md`.

## 1. Objetivo

A materialização mínima deve criar a fundação técnica para que a primeira tarefa funcional do piloto possa começar de forma limpa.

Ela não deve iniciar o domínio do ERP-SAEP.

Em particular, materializar Django não significa implementar:

- usuário por matrícula funcional;
- setores;
- papéis ou permissões do piloto;
- materiais;
- estoque;
- importação SCPI;
- requisições;
- autorizações;
- atendimento;
- notificações;
- auditoria funcional ou linha do tempo de requisição;
- frontend.

A primeira tarefa funcional após esta materialização continua sendo `PIL-BE-ACE-001`.

## 2. Decisões fechadas para a materialização

- O bootstrap será manual mínimo, sem geradores externos de projeto.
- Os apps Django deverão ficar sob `apps/`.
- `config/` será responsável por settings, URLs, ASGI/WSGI e bootstrap.
- Settings iniciais: `config.settings.base`, `config.settings.dev` e `config.settings.test`.
- Não haverá `config.settings.test_postgres` separado.
- PostgreSQL será configurado por `DATABASE_URL`.
- Não será criado `docker-compose.yml` nesta materialização.
- `python-dotenv` será usado para carregar `.env`.
- `DATABASE_URL` será interpretado nos settings com biblioteca padrão do Python.
- `django-cors-headers` será adicionado e configurado de forma conservadora.
- `django.contrib.auth` será habilitado provisoriamente para bootstrap, Admin e DRF.
- `apps/users/` não será criado nesta materialização.
- `django-allauth` pode permanecer como dependência, mas sua configuração será adiada para tarefas de acesso/autenticação.
- Django Admin será habilitado sem modelos de domínio.
- `SECRET_KEY` será obrigatório via ambiente.
- Python 3.14 continuará sendo a versão padrão.
- Dependências devem usar pin por faixa major quando ajustadas.
- Migrations de apps continuam efêmeras e não são entrega versionada.
- `apps/core/` será criado apenas como app técnico transversal de API.
- `/api/v1/schema/` e `/api/v1/docs/` serão criados sem endpoints funcionais de domínio.
- Não haverá healthcheck técnico nesta etapa.
- Testes de smoke ficarão em `tests/` na raiz.
- A CI será genérica de bootstrap e não dependerá de lista fixa de apps futuros.
- `.pre-commit-config.yaml` será criado com hooks de ruff.

## 3. Convenção de tarefas para agentes de IA

Cada tarefa `MAT-*` deve ser tratada como uma unidade independente de implementação técnica.

Formato recomendado de execução:

- **ID:** identificador rastreável da tarefa.
- **Fase:** Materialização mínima Django.
- **Tipo:** Backend, Infraestrutura, Testes, Documentação, CI ou Tooling.
- **Agente sugerido:** perfil de agente mais adequado para executar a tarefa.
- **Depende de:** tarefas `MAT-*` que devem estar concluídas antes.
- **Objetivo:** resultado técnico esperado.
- **Contexto técnico:** decisões e restrições que orientam a implementação.
- **Entregáveis:** arquivos, configurações, testes ou documentação esperados.
- **Testes esperados:** validações mínimas.
- **Comandos de validação:** sempre com `rtk` no ambiente local.
- **Fora do escopo:** itens funcionais `PIL-*` que não podem ser antecipados.

Orientações para agentes:

- Antes de implementar, ler `AGENTS.md`, `.serena/memories/project_overview.md`, `.serena/memories/suggested_commands.md`, `docs/design-acesso-rapido/stack.md` e `docs/design-acesso-rapido/api-contracts.md`.
- Usar `rtk` para comandos shell locais.
- Não criar apps de domínio.
- Não criar `apps/users/` nesta materialização.
- Não gerar nem versionar migrations como entrega.
- Não criar endpoints funcionais de domínio.
- Não introduzir frontend.
- Não adicionar Celery ou Redis.
- Não implementar regras de negócio do ERP-SAEP.

## 4. Backlog de materialização

### MAT-000 — Alinhar documentação pré-materialização

- **Status atual:** não iniciada.
- **Fase:** Materialização mínima Django
- **Tipo:** Documentação
- **Agente sugerido:** Agente técnico/documentação
- **Depende de:** nenhuma
- **Objetivo:** remover ambiguidade documental antes do scaffold Django manual.
- **Contexto técnico:**
  - A decisão vigente é bootstrap manual mínimo, sem geradores externos de projeto.
  - O backlog do piloto deve começar no domínio funcional, não na materialização técnica.
  - `PIL-BE-ACE-001` deve criar `apps/users/` com usuário customizado por matrícula funcional.
- **Entregáveis:**
  - Remover referências a geradores externos de projeto como direção vigente nas docs rastreadas.
  - Ajustar `docs/design-acesso-rapido/stack.md` para descrever a estrutura antes e depois da materialização.
  - Ajustar `docs/backlog/backlog-tecnico-piloto.md` para apontar `MAT-*` como pré-condição técnica.
  - Ajustar a redação de `PIL-BE-ACE-001` para criar `apps/users/`.
  - Atualizar memórias Serena relacionadas por MCP.
- **Testes esperados:**
  - Busca por referências antigas a geradores externos de projeto nas docs rastreadas não deve retornar decisão vigente.
  - Busca por `PIL-BE-ACE-001` deve mostrar que a tarefa cria `apps/users/`.
- **Comandos de validação:**
  - `rtk rg "geradores externos|bootstrap manual" docs .serena/memories`
  - `rtk rg "PIL-BE-ACE-001|apps/users" docs/backlog/backlog-tecnico-piloto.md`
- **Fora do escopo:**
  - Criar `apps/users/`.
  - Alterar modelo de usuário.
  - Implementar login por matrícula.

### MAT-001 — Inspecionar estrutura e confirmar baseline

- **Status atual:** não iniciada.
- **Fase:** Materialização mínima Django
- **Tipo:** Infraestrutura / Documentação
- **Agente sugerido:** Agente backend
- **Depende de:** MAT-000
- **Objetivo:** confirmar o estado real do repositório antes de qualquer scaffold técnico.
- **Contexto técnico:**
  - O repositório era documental no diagnóstico inicial.
  - Não se deve assumir que `manage.py`, `config/` ou `apps/` existem sem verificar.
- **Entregáveis:**
  - Diagnóstico objetivo de arquivos existentes e ausentes.
  - Confirmação de Makefile, pyproject, `uv.lock`, `.env.example` e CI.
  - Confirmação de que não há apps de domínio materializados.
- **Testes esperados:**
  - Não há teste automatizado obrigatório nesta tarefa.
  - A validação é de inspeção.
- **Comandos de validação:**
  - `rtk rg --files`
  - `rtk make help`
  - `rtk git status --short`
- **Fora do escopo:**
  - Criar arquivos Django.
  - Alterar docs além do diagnóstico.
  - Criar qualquer app funcional.

### MAT-002 — Criar bootstrap Django mínimo

- **Status atual:** não iniciada.
- **Fase:** Materialização mínima Django
- **Tipo:** Backend / Infraestrutura
- **Agente sugerido:** Agente backend
- **Depende de:** MAT-001
- **Objetivo:** criar um projeto Django inicializável sem domínio funcional.
- **Contexto técnico:**
  - O bootstrap será manual mínimo.
  - `config/` será responsável por settings, URLs, ASGI/WSGI e bootstrap.
  - Os apps Django ficarão sob `apps/`.
  - `django.contrib.auth` será provisório até `PIL-BE-ACE-001`.
- **Entregáveis:**
  - `manage.py`.
  - Pacote `config/`.
  - `config/urls.py`.
  - `config/asgi.py`.
  - `config/wsgi.py`.
  - Pacote `config/settings/`.
  - Pacote `apps/`.
  - Django Admin habilitado.
- **Testes esperados:**
  - Django deve carregar settings.
  - `manage.py check` deve passar.
- **Comandos de validação:**
  - `rtk make prepare`
  - `rtk make init`
  - `rtk uv run python manage.py check --settings=config.settings.dev`
- **Fora do escopo:**
  - Criar `apps/users/`.
  - Definir usuário customizado.
  - Criar models de domínio.
  - Criar migrations como entrega.

### MAT-003 — Configurar settings, ambiente e PostgreSQL

- **Status atual:** não iniciada.
- **Fase:** Materialização mínima Django
- **Tipo:** Backend / Infraestrutura
- **Agente sugerido:** Agente backend
- **Depende de:** MAT-002
- **Objetivo:** configurar settings mínimos para desenvolvimento e teste com PostgreSQL.
- **Contexto técnico:**
  - Settings iniciais serão `base`, `dev` e `test`.
  - `SECRET_KEY` será obrigatório via ambiente.
  - `.env` será carregado com `python-dotenv`.
  - `DATABASE_URL` será parseado com biblioteca padrão.
  - PostgreSQL é o banco principal desde o início.
- **Entregáveis:**
  - `config/settings/base.py`.
  - `config/settings/dev.py`.
  - `config/settings/test.py`.
  - `.env.example` mínimo Django/API.
  - `pyproject.toml` e `uv.lock` com `python-dotenv` e `django-cors-headers` pinados por faixa major.
  - Configuração conservadora de CORS e CSRF para ambiente local.
- **Testes esperados:**
  - Settings carregam com `.env`.
  - Falha clara quando `SECRET_KEY` estiver ausente.
  - Banco usa `DATABASE_URL`.
- **Comandos de validação:**
  - `rtk make prepare`
  - `rtk make init`
  - `rtk uv run python manage.py check --settings=config.settings.dev`
  - `rtk make test`
- **Fora do escopo:**
  - Criar Docker Compose.
  - Criar settings de produção.
  - Configurar Web Push.
  - Configurar Celery.

### MAT-004 — Configurar testes de smoke

- **Status atual:** não iniciada.
- **Fase:** Materialização mínima Django
- **Tipo:** Testes
- **Agente sugerido:** Agente backend
- **Depende de:** MAT-003
- **Objetivo:** criar testes mínimos que validem o bootstrap Django sem domínio.
- **Contexto técnico:**
  - Testes de smoke devem ficar em `tests/` na raiz.
  - Apps futuros poderão ter testes locais próprios.
  - `pytest-django` já faz parte da stack.
- **Entregáveis:**
  - Diretório `tests/`.
  - Testes de smoke para carregamento de settings e URLs.
  - Ajustes mínimos em `pyproject.toml`, se necessário.
- **Testes esperados:**
  - `pytest` deve passar sem apps de domínio.
  - Nenhum teste deve depender de usuário customizado, material, estoque ou requisição.
- **Comandos de validação:**
  - `rtk make test`
- **Fora do escopo:**
  - Testes de regra de negócio.
  - Testes de API funcional.
  - Testes de permissões do piloto.

### MAT-005 — Configurar DRF/OpenAPI/core API sem domínio

- **Status atual:** não iniciada.
- **Fase:** Materialização mínima Django
- **Tipo:** Backend / API
- **Agente sugerido:** Agente backend/API
- **Depende de:** MAT-004
- **Objetivo:** preparar a infraestrutura comum de API antes dos primeiros endpoints funcionais.
- **Contexto técnico:**
  - A API formal deve seguir `/api/v1/`.
  - DRF, drf-spectacular e django-filter fazem parte da stack.
  - `apps/core/` será técnico e transversal.
  - Rotas de schema e docs podem existir antes de endpoints de domínio.
- **Entregáveis:**
  - App técnico `apps/core/`.
  - Módulos em `apps/core/api/` para paginação, exceções, serializers de erro e helpers de schema.
  - Configuração DRF base.
  - Configuração drf-spectacular base.
  - Configuração django-filter base.
  - Rotas `/api/v1/schema/` e `/api/v1/docs/`.
  - Testes de smoke para schema/docs sem domínio.
- **Testes esperados:**
  - Schema OpenAPI carrega.
  - Docs carregam em dev/test.
  - Paginação e envelope de erro possuem componentes técnicos testáveis.
- **Comandos de validação:**
  - `rtk make test`
  - `rtk uv run python manage.py check --settings=config.settings.dev`
- **Fora do escopo:**
  - Endpoints de usuário, setor, papel, material, estoque, importação, requisição, autorização, atendimento, notificação ou auditoria.
  - Policies de domínio.
  - Services de domínio.

### MAT-006 — Ajustar CI genérica de bootstrap

- **Status atual:** não iniciada.
- **Fase:** Materialização mínima Django
- **Tipo:** CI / Tooling
- **Agente sugerido:** Agente backend/CI
- **Depende de:** MAT-005
- **Objetivo:** validar no CI que a base Django materializada instala, carrega settings e roda testes de smoke.
- **Contexto técnico:**
  - A CI não deve depender de lista fixa de apps de domínio.
  - A CI deve usar `config.settings.test`.
  - Testes PostgreSQL críticos de estoque/reserva só existirão quando o domínio existir.
- **Entregáveis:**
  - `.github/workflows/ci.yml` sem referências a apps futuros inexistentes.
  - Job de lint com ruff.
  - Job de testes com instalação de dependências, PostgreSQL quando necessário, `manage.py check` e pytest.
  - `.pre-commit-config.yaml` com hooks de ruff.
- **Testes esperados:**
  - Lint passa.
  - `manage.py check` passa.
  - Smoke tests passam.
- **Comandos de validação:**
  - `rtk make test`
  - `rtk uv run python manage.py check --settings=config.settings.dev`
  - `rtk uv run ruff check .`
  - `rtk uv run ruff format --check .`
- **Fora do escopo:**
  - CI de concorrência de estoque.
  - CI de schema OpenAPI com endpoints funcionais.
  - Validações de fluxos `PIL-*`.

## 5. Ordem de execução recomendada

1. `MAT-000 — Alinhar documentação pré-materialização`
2. `MAT-001 — Inspecionar estrutura e confirmar baseline`
3. `MAT-002 — Criar bootstrap Django mínimo`
4. `MAT-003 — Configurar settings, ambiente e PostgreSQL`
5. `MAT-004 — Configurar testes de smoke`
6. `MAT-005 — Configurar DRF/OpenAPI/core API sem domínio`
7. `MAT-006 — Ajustar CI genérica de bootstrap`

Após `MAT-006`, iniciar o backlog funcional do piloto em `PIL-BE-ACE-001`.
