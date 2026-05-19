# Arquitetura do Frontend — Piloto

## 1. Objetivo

Definir a arquitetura operacional do frontend do piloto do WMS-SAEP após o abandono da SPA separada, preservando contrato de produto suficiente para orientar as próximas fatias.

Este documento é canônico para:

- stack do frontend;
- escopo ativo do frontend do piloto;
- fronteiras entre backend, templates e interações HTMX;
- superfícies de autenticação, rotas e jornadas;
- worklists, detalhe, formulários e comportamento esperado;
- sequência de reconstrução, seed mínima e validação operacional.

## 2. Escopo ativo

O frontend do piloto volta a ser server-rendered no próprio Django.

Direção vigente:

- templates Django como superfície principal;
- `django-htmx` + HTMX para interações incrementais;
- Tailwind CSS para styling;
- Alpine.js apenas quando HTMX sozinho não entregar a interação com simplicidade suficiente.

O reset atual descarta a fundação SPA anterior. Não preservar:

- diretório `frontend/`;
- Vite;
- React;
- TanStack Router, Query ou Table;
- client TypeScript gerado;
- smoke tests e E2E da SPA.

O objetivo não é abrir uma frente genérica de UI. O frontend do piloto existe para a interface operacional mínima de:

- solicitante;
- auxiliar de setor;
- chefe de setor;
- auxiliar de Almoxarifado;
- chefe de Almoxarifado.

O `superusuário` permanece fora do foco da interface operacional do piloto, usando admin e superfícies técnicas já existentes.

## 3. Princípios

- Backend Django continua dono do domínio, autenticação, autorização e contratos.
- HTMX deve ser a primeira escolha para interações parciais.
- Alpine.js entra só para estado local pequeno, toggle, disclosure, modal simples ou comportamento efêmero similar.
- Não criar uma mini-SPA escondida dentro de templates.
- Linguagem canônica do domínio deve permanecer na interface.
- Regras de negócio continuam no backend.
- UX do piloto segue orientada a worklists, não CRUD genérico.
- Validação local serve à UX; domínio e concorrência continuam no backend.
- Tema claro único, PT-BR, desktop-first com responsividade funcional.

## 4. Stack

- Django templates
- `django-htmx`
- HTMX
- Tailwind CSS
- Alpine.js
- sessão Django com CSRF

Referências externas de implementação:

- `django-htmx`: instalar pacote, registrar `django_htmx`, usar `django_htmx.middleware.HtmxMiddleware`, incluir `{% htmx_script %}` no template base e enviar CSRF em requests HTMX.
- Tailwind CSS: tratar como toolchain de build-time, com classes detectadas por varredura dos templates reais do projeto.
- Alpine.js: usar `x-data`, `x-show`, `x-cloak` e `Alpine.data(...)` apenas para estado local pequeno e reutilizável.

## 5. Estrutura esperada

Estrutura-alvo em alto nível:

- templates Django para páginas completas;
- partials HTMX para listas, filtros, trechos de detalhe, ações inline e fragmentos pós-submit;
- assets compartilhados para base visual, HTMX e Alpine;
- views server-rendered finas, chamando os mesmos services e policies do backend;
- APIs DRF preservadas quando já forem contrato útil para backend/frontend, integrações ou superfícies futuras.

Regras:

- tela completa e navegação principal são responsabilidade de templates server-rendered;
- partial HTMX não duplica regra de domínio;
- estado efêmero local pequeno pode viver em Alpine.js;
- qualquer comportamento que conheça requisição, autorização ou atendimento pertence ao módulo/domínio correspondente, não a um helper genérico opaco.

## 6. Auth e sessão

- autenticação por sessão Django com CSRF;
- frontend opera com um único `papel operacional principal` por usuário no piloto atual;
- `GET /api/v1/auth/me/` continua sendo a base canônica para derivar capacidades e papel;
- HTMX deve enviar `x-csrftoken`;
- sessão expirada deve redirecionar para login ou responder fragmento de erro apropriado ao contexto HTMX;
- capacidades no frontend continuam derivadas do `papel`.

Superfície esperada:

- `GET /api/v1/auth/csrf/`
- `POST /api/v1/auth/login/`
- `POST /api/v1/auth/logout/`
- `GET /api/v1/auth/me/`

## 7. Rotas e jornadas

Rotas/telas canônicas do piloto:

- `/login`
- `/minhas-requisicoes`
- `/requisicoes/nova`
- `/requisicoes/{id}`
- `/autorizacoes`
- `/atendimentos`
- superfície explícita para papel desconhecido ou desalinhamento de contrato/cadastro

Regras:

- login é server-rendered e pode usar HTMX para submit/feedback sem virar fluxo client-heavy;
- `Minhas requisições` é a lista de trabalho pessoal do usuário;
- `Nova requisição` e edição de rascunho compartilham a mesma estrutura-base;
- detalhe de requisição é canônico e muda ações conforme contexto;
- `Autorizações` e `Atendimentos` são worklists especializadas, não variantes cosméticas da mesma lista;
- papel desconhecido não deve gerar loop de login e deve explicitar desalinhamento de contrato/cadastro.

Homes por papel:

- não há dashboard genérico obrigatório;
- o redirecionamento pós-login deve levar o usuário para a worklist mais útil ao seu papel;
- qualquer fallback neutro deve ser transitório e explícito.

## 8. Bloco 0 e superfícies habilitadoras

Antes de implementar as telas operacionais do frontend, o backend deve entregar:

1. Auth/sessão:
   - `GET /api/v1/auth/csrf/`
   - `POST /api/v1/auth/login/`
   - `POST /api/v1/auth/logout/`
   - `GET /api/v1/auth/me/`
2. Lookup de beneficiário:
   - `GET /api/v1/users/beneficiary-lookup/?q=...`
3. Leituras canônicas de requisição:
   - `GET /api/v1/requisitions/`
   - `GET /api/v1/requisitions/mine/`
   - `GET /api/v1/requisitions/{id}/`
4. Update explícito de rascunho:
   - operação de atualização por substituição completa do rascunho

Regras complementares:

- lookup de beneficiário busca por nome;
- mínimo de 3 caracteres;
- retorno curto, sem paginação;
- só usuários ativos e aptos ao fluxo;
- `GET /api/v1/requisitions/` continua representando visibilidade operacional ampla;
- `GET /api/v1/requisitions/mine/` alimenta `Minhas requisições`;
- ambas as listas devem suportar paginação, busca textual simples e filtro por status quando expostas na interface;
- lista de requisições usa serializer próprio e mais leve que o detalhe.

## 9. Sequência de reconstrução

1. Definir base de templates, layout, assets e barra de navegação/autenticação.
2. Integrar `django-htmx`.
3. Integrar pipeline de Tailwind CSS.
4. Introduzir Alpine.js apenas onde houver lacuna real de UX.
5. Reconstruir `Minhas requisições` + detalhe canônico.
6. Reconstruir criação/edição de rascunho + envio.
7. Reconstruir fila de autorizações.
8. Reconstruir fila de atendimento.
9. Tratar notificações e refinamentos como segunda onda.

## 10. Worklists e detalhe

### Minhas requisições

- todos papéis podem acessar;
- lista única;
- consome `GET /api/v1/requisitions/mine/`, não a lista operacional ampla;
- mostrar `numero_publico` ou badge `Rascunho`;
- destacar beneficiário quando for diferente do usuário logado;
- beneficiário terceiro só enxerga a requisição depois que ela sai de `rascunho`; se ela voltar para `rascunho`, deve sumir da lista e o detalhe passa a responder `404`;
- ordenar por atualização mais recente;
- filtros mínimos: busca textual e status;
- datas exibidas são derivadas contextualmente do status.

### Fila de autorizações

- worklist especializada;
- ordenação por mais antigas pendentes primeiro;
- detalhe abre em contexto de autorização;
- ação rápida esperada: `Autorizar tudo como solicitado`.

### Fila de atendimento

- worklist especializada;
- ordenação por mais antigas autorizadas primeiro;
- detalhe abre em contexto de atendimento;
- ação rápida esperada: `Preencher entrega completa`.

### Detalhe canônico

- cabeçalho comum;
- corpo comum com itens, status e resumo de eventos;
- bloco de ações muda conforme contexto;
- quando a requisição estiver em `rascunho`, pode reutilizar os mesmos blocos centrais da montagem/edição de rascunho.

## 11. Formulários e comportamento

- criação e edição de rascunho usam a mesma tela;
- atualização de rascunho é por substituição completa;
- formulários de ação são action-oriented:
  - criar requisição
  - enviar para autorização
  - autorizar
  - recusar
  - atender
  - cancelar requisição autorizada
- tabelas/listas devem destacar `quantidade_solicitada`, `quantidade_autorizada` e `quantidade_entregue` com apresentação contextual;
- divergências entre quantidades devem ser destacadas visualmente;
- justificativas parciais devem aparecer inline de forma compacta;
- HTMX deve ser preferido para filtros, reload de listas, submit parcial e feedback de ações;
- Alpine.js só deve assumir toggle, disclosure, modal simples, tabs simples ou estado efêmero similar.

## 12. Seed mínima e operação local

Deve existir um comando oficial de backend para popular o cenário mínimo do piloto:

- nome canônico: `seed_pilot_minimo`
- exposto por `rtk make seed-pilot-minimo`

Conteúdo mínimo:

- usuários operacionais principais;
- 1 usuário inativo apenas para autenticação;
- setores coerentes;
- materiais:
  - ativo com saldo confortável
  - ativo com saldo baixo
  - ativo sem estoque associado
  - inativo
- requisições de exemplo:
  - rascunho
  - aguardando autorização
  - autorizada com caso de autorização parcial
  - atendida parcialmente
  - ao menos uma criada para terceiro

Fluxo operacional esperado no ambiente efêmero:

- rodar `rtk make setup`
- rodar `rtk make seed-pilot-minimo`
- usar esse mesmo cenário como baseline para validação manual local

## 13. Validação e checks

Enquanto a nova infraestrutura server-rendered não ganhar suite própria, o mínimo esperado é:

- checks backend existentes continuam obrigatórios;
- cada nova fatia do frontend deve introduzir seus próprios testes e evidências;
- validação manual deve usar a seed mínima oficial do piloto;
- mudanças de contrato continuam exigindo atualização de OpenAPI, testes e documentação.

## 14. Guardrails

- Não recriar `frontend/` sem nova decisão explícita.
- Não mover regra de negócio para JavaScript.
- Não introduzir Alpine.js para fluxos que podem ser resolvidos por HTMX + HTML sem perda relevante.
- Não manter documentação ativa apontando para React/Vite/TanStack como stack vigente.
- Não tratar o admin do Django como substituto da interface operacional do piloto.
