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
- Tema claro único, PT-BR, com responsividade definida por jornada.

## 4. Stack

- Django templates
- `django-htmx`
- HTMX
- Tailwind CSS
- Alpine.js
- sessão Django com CSRF

Referências externas de implementação:

- `django-htmx`: instalar pacote, registrar `django_htmx`, usar `django_htmx.middleware.HtmxMiddleware`, incluir `{% htmx_script %}` no template base e enviar CSRF em requests HTMX.
- Tailwind CSS: usar Tailwind CSS v4 em modo CSS-first, com classes detectadas por varredura dos templates reais do projeto.
- Alpine.js: usar `x-data`, `x-show`, `x-cloak` e `Alpine.data(...)` apenas para estado local pequeno e reutilizável.

### Tailwind CSS

O projeto usa Tailwind CSS v4 em modo CSS-first.

Arquivo oficial de entrada:

- `apps/web/static/web/src/styles.css`

Arquivo oficial compilado:

- `apps/web/static/web/dist/app.css`

O arquivo de entrada deve importar Tailwind com:

```css
@import "tailwindcss";
```

Tokens visuais do projeto devem ser definidos no próprio CSS por meio de `@theme`.

Templates Django devem ser registrados explicitamente com `@source`, cobrindo os diretórios oficiais de templates do app `web` e quaisquer outros diretórios autorizados pela arquitetura.

O CSS compilado `app.css` não deve ser editado manualmente. Agentes devem alterar apenas `styles.css` e templates autorizados.

O projeto deve expor scripts oficiais para desenvolvimento e build:

```json
{
  "scripts": {
    "css:dev": "tailwindcss -i apps/web/static/web/src/styles.css -o apps/web/static/web/dist/app.css --watch",
    "css:build": "tailwindcss -i apps/web/static/web/src/styles.css -o apps/web/static/web/dist/app.css --minify"
  }
}
```

O template base deve carregar apenas o CSS compilado:

```django
{% load static %}
<link rel="stylesheet" href="{% static 'web/dist/app.css' %}">
```

Regras:

- não usar Tailwind via CDN no app real;
- CDN só pode ser usado em protótipos descartáveis e não deve ser commitado como base de implementação;
- não criar `tailwind.config.js` por hábito;
- um arquivo de configuração JavaScript só pode ser criado se houver necessidade técnica explícita, como plugin ou configuração não atendida pelo modelo CSS-first, e essa decisão deve ser registrada na documentação;
- não montar classes Tailwind dinamicamente em templates ou JavaScript, como `class="bg-{{ color }}-600"`;
- classes devem ser escritas de forma completa e detectável pelo build, ou mapeadas por meio de variantes explícitas documentadas;
- uso de `@layer components`, `@apply` e CSS customizado deve ser limitado a recipes ou utilitários realmente estáveis, repetidos e documentados;
- o padrão continua sendo usar Tailwind utilities nos templates seguindo tokens e recipes oficiais do design system.

### Contrato HTMX

O projeto adota um contrato HTMX global mínimo com detalhes específicos por jornada.

HTMX deve ser usado como progressive enhancement para interações server-rendered. Endpoints HTMX não devem retornar HTML arbitrário. Toda action HTMX deve declarar:

- partial renderizado;
- target esperado;
- swap esperado;
- status HTTP esperado;
- headers HTMX utilizados;
- eventos emitidos;
- comportamento em erro;
- teste mínimo obrigatório.

Páginas completas e partials HTMX devem ficar na mesma jornada:

- `apps/web/templates/web/pages/<jornada>/<page>.html`;
- `apps/web/templates/web/pages/<jornada>/_<partial>.html`.

Contrato global de status:

- `200 OK`: operação bem-sucedida com fragmento HTML para swap;
- `204 No Content`: operação bem-sucedida sem fragmento HTML; deve emitir evento HTMX quando houver efeito na UI;
- `400 Bad Request`: request inválido ou parâmetros malformados;
- `401 Unauthorized`: usuário não autenticado ou sessão expirada; não renderizar login dentro de target parcial; usar `HX-Redirect` para tela de login ou `HX-Refresh` quando aplicável;
- `403 Forbidden`: usuário autenticado sem permissão; renderizar feedback seguro e não vazar dados;
- `404 Not Found`: recurso inexistente; renderizar feedback contextual ou global;
- `409 Conflict`: conflito de domínio ou estado concorrente, como recurso já processado, status alterado ou estoque indisponível;
- `422 Unprocessable Entity`: validação de formulário falhou; renderizar a partial do formulário com erros por campo e erro global quando aplicável;
- `500 Internal Server Error`: erro inesperado; renderizar feedback genérico e registrar erro no backend.

Targets HTMX devem usar IDs estáveis e documentados, por exemplo:

```html
<div id="global-feedback" aria-live="polite"></div>
<div id="modal-root"></div>
<div id="requisitions-table"></div>
<div id="requisition-form"></div>
```

Não é permitido usar targets frágeis baseados em estrutura visual instável, como seletores dependentes de `nth-child` ou hierarquia profunda.

Swaps permitidos por padrão:

- `innerHTML`;
- `outerHTML`;
- `beforeend`;
- `afterbegin`;
- `none`.

Headers HTMX permitidos mediante necessidade documentada:

- `HX-Redirect`;
- `HX-Refresh`;
- `HX-Trigger`;
- `HX-Trigger-After-Swap`;
- `HX-Trigger-After-Settle`;
- `HX-Retarget`;
- `HX-Reswap`;
- `HX-Reselect`.

Sessão expirada em request HTMX deve resultar em redirecionamento ou refresh controlado. Não é permitido injetar a tela de login dentro de uma partial.

Validação de formulário deve retornar `422` com a partial do formulário renderizada com erros. Permissão negada deve retornar `403`. Conflitos de domínio devem retornar `409`.

Novas actions HTMX devem usar helpers padronizados de resposta sempre que possível, em vez de escrever headers manualmente em cada view.

Alpine.js pode reagir a eventos emitidos por HTMX, mas não deve duplicar regra de negócio, autorização ou validação que pertence ao backend.

## 4.1 Design system

O design system do projeto segue um modelo híbrido, token/recipe-first.

Tokens e recipes são a base obrigatória para orientar:

- layout;
- cores;
- tipografia;
- espaçamento;
- bordas;
- sombras;
- estados de UI;
- responsividade;
- padrões de composição.

Templates Django reutilizáveis em `apps/web/templates/web/components/` devem ser usados apenas para componentes repetidos, pequenos, semanticamente estáveis e com variações controladas.

Por padrão, novos padrões visuais começam como recipes documentadas. Um padrão só deve ser promovido para include Django quando atender a pelo menos quatro critérios:

- aparece em três ou mais telas;
- possui semântica clara;
- possui variações limitadas;
- exige acessibilidade consistente;
- possui estados padronizados;
- não depende fortemente do contexto da página;
- pode ter API simples;
- sua alteração centralizada reduz manutenção.

Includes oficiais iniciais:

- `apps/web/templates/web/components/button.html`;
- `apps/web/templates/web/components/badge.html`;
- `apps/web/templates/web/components/alert.html`;
- `apps/web/templates/web/components/form_field.html`;
- `apps/web/templates/web/components/empty_state.html`;
- `apps/web/templates/web/components/pagination.html`;
- `apps/web/templates/web/components/modal_shell.html`.

Layouts de página, grids, dashboards, tabelas completas, toolbars e estruturas complexas de formulário devem começar como recipes documentadas, não como includes genéricos.

Tailwind CSS pode ser usado diretamente no markup desde que siga os tokens e recipes oficiais. Não é permitido criar variações visuais arbitrárias sem atualizar a documentação do design system.

Componentes Django não devem conter regra de negócio, consultas, permissões ou cálculos de workflow. Eles devem receber dados simples e renderizar marcação acessível e consistente.

Alpine.js só pode ser embutido em componentes quando o comportamento for local, progressivo e documentado, como modal, dropdown, tabs ou toggle.

## 5. Estrutura esperada

Estrutura-alvo em alto nível:

- app `apps/web` como único responsável por composição visual, shell, layouts, navegação, design system, templates de página, partials operacionais, assets globais de UI e views que renderizam HTML;
- apps de domínio (`requisitions`, `users`, `stock`, `materials` e equivalentes) responsáveis por models, forms, selectors, services, policies, validações, permissões e context builders;
- templates Django para páginas completas em `apps/web/templates/web/pages/<jornada>/`;
- partials HTMX operacionais em `apps/web/templates/web/pages/<jornada>/`, próximos da jornada que atualizam;
- componentes compartilhados em `apps/web/templates/web/components/`;
- layouts e shells em `apps/web/templates/web/layouts/`;
- assets globais de Tailwind CSS e Alpine.js em `apps/web/static/web/`;
- views server-rendered finas em `apps/web`, chamando services, selectors, policies, forms e context builders dos apps de domínio;
- APIs DRF preservadas quando já forem contrato útil para backend/frontend, integrações ou superfícies futuras.

Regras:

- tela completa e navegação principal são responsabilidade de templates server-rendered;
- partial HTMX não duplica regra de domínio;
- estado efêmero local pequeno pode viver em Alpine.js;
- qualquer comportamento que conheça requisição, autorização ou atendimento pertence ao módulo/domínio correspondente, não a um helper genérico opaco.
- não criar templates de página em `apps/<domain>/templates/` sem decisão arquitetural explícita;
- não duplicar `base.html`, criar layouts paralelos ou espalhar partials entre apps de domínio;
- views em `apps/web` podem orquestrar renderização, mas não devem conter regra de negócio, queries complexas ou decisões de permissão;
- Alpine.js deve ser usado apenas para comportamento local e progressivo de UI;
- Tailwind CSS deve seguir os tokens e recipes documentados no design system do projeto.

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

## 11.1 Shell, navegação e responsividade

O projeto usa um shell único, responsivo e mobile-safe, com navegação orientada por papel e permissão. Não serão criados shells separados para mobile e desktop no MVP.

Toda nova jornada deve declarar sua categoria responsiva antes da implementação. Essa categoria define layout, comportamento de tabela/lista, filtros, ações, densidade visual e critérios de aceite.

Categorias:

- `mobile-primary`;
- `desktop-optimized`;
- `responsive-neutral`.

Jornadas `mobile-primary` são aquelas usadas principalmente por solicitantes, chefias ou usuários em campo, como:

- nova solicitação;
- minhas solicitações;
- detalhe da solicitação;
- aprovação/rejeição;
- acompanhamento de status.

Essas jornadas devem priorizar layout mobile-first, ações principais visíveis, formulários de uma coluna, listas/cards em mobile e baixa densidade visual.

Jornadas `desktop-optimized` são aquelas usadas principalmente pelo Almoxarifado ou operação interna, como:

- fila de atendimento;
- estoque;
- movimentações;
- materiais;
- inventário;
- separação/atendimento.

Essas jornadas devem preservar densidade em desktop, tabelas, filtros, comparação de dados e produtividade operacional. Elas devem funcionar em mobile, mas não precisam oferecer a mesma densidade de informação da experiência desktop.

Jornadas `responsive-neutral` são telas secundárias ou administrativas sem contexto operacional dominante.

O shell oficial deve conter:

- header;
- navegação por papel/permissão;
- sidebar em desktop;
- drawer/menu colapsável em mobile;
- área global de feedback;
- modal root;
- page header;
- ações principais da página.

A navegação não deve refletir a estrutura técnica dos apps Django. Ela deve refletir tarefas do usuário por papel.

Não é permitido:

- criar shell mobile separado sem decisão formal;
- depender de hover para ações críticas;
- esconder ação crítica em mobile;
- usar tabela larga sem estratégia responsiva;
- criar menu baseado apenas em módulos técnicos;
- aceitar "não quebrar no celular" como critério suficiente para jornada `mobile-primary`.

## 11.2 Acessibilidade

Acessibilidade é tratada como contrato obrigatório de implementação, não como checklist final.

WCAG AA é o objetivo geral, mas a implementação do projeto é guiada por contratos obrigatórios por primitive, componente, partial HTMX e jornada.

Todo componente ou primitive oficial deve declarar seus requisitos mínimos de acessibilidade. Isso inclui, quando aplicável:

- nome acessível;
- label visível ou equivalente semântico;
- foco visível;
- navegação por teclado;
- estado disabled;
- estado loading;
- mensagens de erro;
- associação entre erro e campo;
- `aria-live` para feedback dinâmico;
- comportamento após swap HTMX.

Todo formulário deve garantir:

- campos com label ou nome acessível;
- erros por campo associados com `aria-describedby`;
- `aria-invalid="true"` em campos inválidos;
- erro global quando necessário;
- foco no primeiro erro ou no resumo de erros após validação;
- botão submit com `type` explícito;
- estado loading/disabled durante submissão.

Toda action HTMX que atualiza conteúdo relevante deve declarar:

- target atualizado;
- feedback exibido;
- região `aria-live` utilizada;
- foco após sucesso;
- foco após erro;
- comportamento em `422`;
- comportamento em `403`;
- comportamento em `409`.

O shell deve fornecer regiões globais de feedback:

```html
<div id="global-feedback" aria-live="polite" aria-atomic="true"></div>
<div id="global-errors" aria-live="assertive" aria-atomic="true"></div>
```

Modais devem usar o modal shell oficial e garantir:

- nome acessível;
- `aria-modal` ou comportamento equivalente;
- foco inicial ao abrir;
- retorno de foco ao fechar;
- fechamento por teclado quando permitido;
- ações claras;
- não dependência exclusiva de clique fora.

Não é permitido:

- ação dependente apenas de hover;
- ícone interativo sem nome acessível;
- erro indicado apenas por cor;
- campo inválido sem `aria-invalid`;
- erro de campo sem associação semântica;
- modal sem controle de foco;
- action HTMX que altera conteúdo sem feedback;
- `div` clicável sem semântica e teclado.

Novas jornadas e novos componentes devem incluir critérios mínimos de acessibilidade nos testes de contrato HTML/HTMX. Acessibilidade deve ser validada durante a implementação, não apenas no gate final.

## 11.3 Segurança frontend

O projeto adota uma política de segurança frontend baseada em secure defaults pragmáticos para Django server-rendered, HTMX e Alpine.js.

Atributos declarativos de HTMX e Alpine.js são permitidos, desde que usados apenas para comportamento local de UI e sem expor dados sensíveis, regras de negócio, permissões internas ou segredos no HTML.

Scripts inline soltos em templates e partials são proibidos. Handlers nativos como `onclick`, `onchange`, `onload` e similares também são proibidos. O comportamento interativo deve ser implementado por atributos HTMX/Alpine permitidos ou por arquivos JavaScript externos versionados em `apps/web/static/web/`.

O autoescape padrão do Django deve permanecer habilitado. Não é permitido usar `{{ value|safe }}` sem decisão explícita, sanitização adequada e justificativa registrada. Conteúdo vindo de usuário, como observações, comentários, justificativas e descrições, deve ser renderizado como texto, não como HTML confiável. Não é permitido interpolar dados de usuário ou dados vindos do backend diretamente dentro de JavaScript inline ou expressões Alpine complexas.

Dados JSON enviados do backend para o frontend devem ser renderizados com `json_script` ou mecanismo equivalente seguro. Não é permitido montar JSON manualmente em templates Django. O HTML deve conter apenas os dados mínimos necessários para a renderização da tela e autorizados para o usuário atual. Tokens, segredos, permissões internas completas, payloads administrativos, regras de negócio e dados sensíveis desnecessários não devem ser colocados no DOM.

HTMX deve usar CSRF em toda requisição mutável, incluindo `POST`, `PUT`, `PATCH` e `DELETE`. O token CSRF deve ser aplicado por padrão no shell ou em ancestor comum usando `hx-headers` com JSON estático seguro, ou por helper equivalente aprovado. Não é permitido usar `hx-headers` com `javascript:` ou `js:` para calcular headers dinamicamente.

Endpoints HTMX devem aplicar autenticação e autorização no backend. Esconder botão no frontend nunca substitui checagem de permissão no endpoint.

Redirects HTMX devem ser restritos a rotas internas validadas. Não é permitido preencher `HX-Redirect` diretamente com parâmetros não validados, como `next` vindo da query string. Sessão expirada em request HTMX deve retornar `401` com `HX-Redirect` ou `HX-Refresh`, sem renderizar a tela de login dentro de uma partial.

Alpine.js deve ser usado apenas para estado local e progressivo de UI, como modal, dropdown, tabs, toggle, seleção visual e loading. Alpine.js não deve conter regra de negócio, autorização, validação de domínio ou dados sensíveis. O uso de `x-html` com conteúdo vindo do backend ou de usuário é proibido. Expressões Alpine devem ser pequenas; lógica complexa deve ser movida para JavaScript externo controlado.

A CSP deve ser planejada desde o início. No MVP, a política pode começar pragmática e, quando necessário, em modo report-only, mas o projeto deve evitar padrões que impeçam endurecimento futuro. A meta de evolução é restringir scripts a arquivos externos confiáveis e/ou mecanismos com nonce ou hash, removendo dependências de inline script inseguro.

Links externos abertos com `target="_blank"` devem usar `rel="noopener noreferrer"`. HTMX não deve chamar rotas externas. Fragments HTMX devem seguir as mesmas regras de escaping, permissão, CSRF e minimização de dados aplicadas a páginas completas.

Agentes de IA não devem criar scripts inline, não devem usar `|safe`, não devem montar JSON manualmente, não devem colocar dados sensíveis no DOM, não devem criar endpoint HTMX mutável sem CSRF, não devem implementar autorização apenas no frontend e não devem usar redirects externos ou não validados. Qualquer exceção de segurança deve ser registrada como decisão arquitetural explícita antes da implementação.

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

Toda nova jornada server-rendered com HTMX deve possuir testes mínimos de contrato usando Django test client e assertions HTML/HTMX.

Mínimo obrigatório por página completa:

- `GET` da página por usuário autorizado;
- status `200`;
- template correto;
- contexto essencial presente;
- targets HTMX oficiais presentes;
- região de feedback presente quando aplicável;
- ações visíveis conforme permissão;
- ações proibidas ausentes para usuário sem permissão;
- empty state renderizado quando não houver dados;
- atributos básicos de acessibilidade presentes.

Mínimo obrigatório por action HTMX:

- request HTMX válida retorna `200` ou `204`;
- partial correta é renderizada quando houver HTML;
- headers HTMX esperados estão presentes;
- target e swap esperados são compatíveis com a página;
- request inválida de formulário retorna `422`;
- erros de campo e erro global são renderizados quando aplicável;
- usuário autenticado sem permissão recebe `403`;
- usuário não autenticado ou sessão expirada recebe `401` com `HX-Redirect` ou `HX-Refresh`;
- conflito de domínio retorna `409` quando aplicável;
- endpoint não retorna página completa quando deveria retornar partial;
- endpoint não injeta tela de login dentro de target parcial.

Snapshots HTML são permitidos apenas para fragments pequenos e estáveis. O padrão deve ser usar assertions semânticas sobre IDs, atributos `hx-*`, headers, mensagens, estados e atributos de acessibilidade. Snapshots de página inteira não são recomendados como teste padrão.

Playwright não é obrigatório para toda jornada no início do projeto. Porém, Playwright é obrigatório para fluxos críticos ou gates de lançamento que envolvam:

- operação crítica de negócio;
- operação destrutiva;
- modal com submit;
- HTMX + Alpine.js no mesmo fluxo;
- múltiplos swaps;
- atualização parcial de tabela;
- redirect pós-sucesso;
- evento HTMX consumido no frontend;
- aprovação ou rejeição;
- movimentação de estoque;
- mudança de permissão;
- regressão já identificada.

Agentes de IA não devem criar nova página ou action HTMX sem incluir os testes mínimos correspondentes. Toda action HTMX deve ter pelo menos testes de sucesso, permissão e erro esperado. Formulários HTMX devem obrigatoriamente testar `422`. Ações sujeitas a estado concorrente ou regra operacional devem obrigatoriamente testar `409`.

## 14. Guardrails

- Não recriar `frontend/` sem nova decisão explícita.
- Não mover regra de negócio para JavaScript.
- Não introduzir Alpine.js para fluxos que podem ser resolvidos por HTMX + HTML sem perda relevante.
- Não manter documentação ativa apontando para React/Vite/TanStack como stack vigente.
- Não tratar o admin do Django como substituto da interface operacional do piloto.
