# Arquitetura do Frontend — Piloto

## Sumário operacional

Use este sumário como rota rápida para implementação e revisão. Para novas issues/PRs, comece pelo handoff e depois consulte as seções específicas da jornada.

- [Objetivo](#1-objetivo)
- [Escopo ativo](#2-escopo-ativo)
- [Princípios](#3-princípios)
- [Stack](#4-stack)
  - [Tailwind CSS](#tailwind-css)
  - [Contrato HTMX](#contrato-htmx)
- [Design system](#41-design-system)
  - [Contrato fino dos includes oficiais](#contrato-fino-dos-includes-oficiais)
  - [Direção visual](#direção-visual)
- [Estrutura esperada](#5-estrutura-esperada)
  - [Camada de apresentação](#camada-de-apresentação)
- [Auth e sessão](#6-auth-e-sessão)
  - [Autenticação HTML](#autenticação-html)
- [Rotas e jornadas](#7-rotas-e-jornadas)
  - [URLs HTML](#urls-html)
  - [Navegação principal](#navegação-principal)
- [Bloco 0 e superfícies habilitadoras](#8-bloco-0-e-superfícies-habilitadoras)
- [Sequência de reconstrução e delivery](#9-sequência-de-reconstrução-e-delivery)
  - [PR1 — Fundação mínima](#pr1--fundação-mínima-do-frontend-server-rendered)
  - [PR2 — Primeira jornada real](#pr2--primeira-jornada-real-usando-a-fundação)
  - [Frontend Handoff Contract](#frontend-handoff-contract)
- [Worklists e detalhe](#10-worklists-e-detalhe)
  - [Recipe de worklist](#recipe-de-worklist)
  - [Detalhe canônico](#detalhe-canônico)
- [Formulários e comportamento](#11-formulários-e-comportamento)
  - [Ações críticas](#ações-críticas)
  - [Nova solicitação e edição de rascunho](#nova-solicitação-e-edição-de-rascunho)
  - [Formulários server-rendered](#formulários-server-rendered)
- [Shell, navegação e responsividade](#111-shell-navegação-e-responsividade)
- [Acessibilidade](#112-acessibilidade)
- [Segurança frontend](#113-segurança-frontend)
- [Erros, suporte e trace ID](#114-erros-suporte-e-trace-id)
- [Estados de UI por jornada](#115-estados-de-ui-por-jornada)
- [Seed mínima e operação local](#12-seed-mínima-e-operação-local)
- [Validação e checks](#13-validação-e-checks)
- [Guardrails](#14-guardrails)

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

Helpers HTMX oficiais mínimos devem viver preferencialmente em `apps/web/htmx.py`:

- `render_htmx(request, template, context, *, status=200)`;
- `htmx_redirect(url, *, status=401|200)`;
- `htmx_refresh(*, status=401|200)`;
- `htmx_trigger(response, event, payload=None, after="receive|swap|settle")`;
- `htmx_retarget(response, target)`;
- `htmx_validation_error(request, template, context)`;
- `htmx_forbidden(request, template, context)`;
- `htmx_conflict(request, template, context)`;
- `htmx_session_expired(login_url)`.

Views não devem escrever headers HTMX manualmente sem justificativa. Se uma action exigir header não coberto pelo helper existente, o PR deve adicionar helper pequeno e genérico ou registrar a exceção.

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

### Contrato fino dos includes oficiais

Os includes oficiais do design system devem ter contrato fino documentado antes do PR1, sem tentar definir uma API completa e definitiva para todos os casos futuros.

O projeto não deve deixar o PR1 descobrir livremente a API dos componentes, porque includes Django com parâmetros inconsistentes viram dívida rapidamente. Também não deve criar uma API extensa e genérica demais antes de validar o uso real em jornadas.

A decisão oficial é documentar agora propósito, escopo, variantes permitidas, requisitos de acessibilidade, regras de uso e limites de cada include oficial inicial. Parâmetros exatos podem ser refinados no PR1 desde que respeitem este contrato.

Esses componentes devem ser pequenos, previsíveis e semanticamente estáveis. Eles não devem tentar resolver todos os casos visuais do sistema. Componentes grandes, contextuais ou muito variáveis devem permanecer como recipes documentadas ou partials específicas de jornada.

Todo include oficial deve declarar:

- propósito;
- quando usar;
- quando não usar;
- variantes permitidas;
- parâmetros mínimos;
- parâmetros proibidos;
- requisitos de acessibilidade;
- requisitos de segurança;
- exemplo canônico de uso;
- critérios de teste.

A API de um include deve ser pequena. Um componente que exigir muitos parâmetros provavelmente está abstrato demais e deve voltar para recipe ou partial específica da jornada.

Não é permitido criar includes genéricos com APIs amplas, como:

- `action.html`;
- `widget.html`;
- `panel.html`;
- `block.html`;
- `layout.html`;
- `table.html` genérico demais;
- `card.html` genérico demais.

Exceções exigem decisão documentada posterior.

Princípios obrigatórios:

- receber dados simples;
- não executar regra de negócio;
- não fazer query;
- não decidir permissão;
- não calcular status de workflow;
- não conter lógica de domínio;
- não depender de model inteiro quando um valor simples basta;
- não renderizar HTML inseguro;
- não usar scripts inline soltos;
- não usar Alpine.js para regra de negócio;
- não aceitar classes arbitrárias como mecanismo primário de customização.

Permissão deve ser decidida antes do include. O componente pode receber um booleano simples como `disabled` ou `hidden` apenas quando isso representar estado visual já decidido pela view/context builder, mas não deve receber objetos de usuário, roles, policies ou permissões brutas para decidir autorização.

Parâmetros devem ser explícitos, pequenos e semânticos.

Parâmetros permitidos por padrão, quando fizerem sentido para o componente:

- `variant`;
- `size`;
- `label`;
- `href`;
- `type`;
- `disabled`;
- `loading`;
- `id`;
- `name`;
- `value`;
- `describedby`;
- `testid`.

Parâmetros HTMX são permitidos apenas em componentes de ação quando forem necessários e documentados:

- `hx_get`;
- `hx_post`;
- `hx_target`;
- `hx_swap`;
- `hx_confirm`;
- `hx_trigger`.

O uso de parâmetros HTMX deve permanecer simples. Se um botão exigir muitos atributos HTMX, comportamento condicional complexo ou eventos específicos, a marcação deve ficar explícita na partial da jornada ou virar recipe, não ser escondida em include genérico.

Parâmetros proibidos por padrão:

- `user`;
- `request`;
- `permission`;
- `policy`;
- `model`;
- `object`;
- `queryset`;
- `raw_html`;
- `unsafe_html`;
- `script`;
- `onclick`;
- `onchange`;
- `style`;
- `class` arbitrária sem regra.

O uso de `extra_classes` ou parâmetro equivalente deve ser evitado como padrão. Ele só pode existir se a documentação definir claramente que é exceção controlada, não mecanismo normal de variação visual. Variações recorrentes devem virar `variant` ou recipe documentada.

#### `button.html`

Propósito: renderizar ações clicáveis consistentes e acessíveis.

Usar para:

- ação primária;
- ação secundária;
- ação destrutiva;
- link com aparência de botão;
- submit de formulário;
- botão HTMX simples.

Não usar para:

- links comuns dentro de texto;
- ícones isolados sem nome acessível;
- ações com markup interno complexo;
- menus de ação compostos;
- autorização ou regra de negócio.

Variantes permitidas:

- `primary`;
- `secondary`;
- `outline`;
- `ghost`;
- `danger`.

Tamanhos permitidos:

- `sm`;
- `md`;
- `lg`.

Tipos permitidos quando renderizar `<button>`:

- `button`;
- `submit`;
- `reset`.

Requisitos obrigatórios:

- todo botão deve ter nome acessível;
- todo `button` deve ter `type` explícito;
- `disabled` deve ser semanticamente representado;
- `loading` deve impedir duplo submit quando aplicável;
- `danger` deve ser usado apenas para ação destrutiva;
- ícone sem texto visível exige `aria-label`;
- botão HTMX mutável deve respeitar CSRF via shell/helper.

O componente não deve decidir se a action é permitida. A view/template deve decidir se o botão aparece ou se fica `disabled`.

Exemplo:

```django
{% include "web/components/button.html" with label="Salvar" variant="primary" type="submit" %}
{% include "web/components/button.html" with label="Cancelar solicitação" variant="danger" hx_post=cancel_url hx_target="#modal-root" hx_swap="innerHTML" %}
```

Exemplo proibido:

```django
{% include "web/components/button.html" with user=request.user permission="requisitions.cancel" object=requisition %}
```

#### `badge.html`

Propósito: renderizar status, estados e classificações curtas com aparência consistente.

Usar para:

- status de requisição;
- status de estoque;
- estado de aprovação;
- nível de alerta;
- classificação curta.

Não usar para:

- texto longo;
- mensagens de erro completas;
- botões;
- links principais;
- decisões de permissão.

Variantes semânticas permitidas:

- `neutral`;
- `info`;
- `success`;
- `warning`;
- `danger`.

Requisitos obrigatórios:

- status iguais devem usar a mesma variante em todo o sistema;
- badge não pode depender apenas de cor para transmitir significado;
- texto visível deve ser claro;
- não passar status bruto sem mapeamento semântico documentado.

O mapeamento entre status de domínio e variante visual deve ser feito em context builder, policy de apresentação ou helper documentado, não dentro do include com lógica de domínio.

Exemplo:

```django
{% include "web/components/badge.html" with label=requisition.status_label variant=requisition.status_variant %}
```

Exemplo proibido:

```django
{% include "web/components/badge.html" with object=requisition %}
```

#### `alert.html`

Propósito: renderizar feedback textual acessível para sucesso, erro, alerta, informação, permissão e conflito.

Usar para:

- mensagem de sucesso;
- erro global;
- aviso;
- informação contextual;
- permissão negada;
- conflito de domínio.

Variantes permitidas:

- `info`;
- `success`;
- `warning`;
- `danger`.

Requisitos obrigatórios:

- mensagem textual clara;
- não depender apenas de cor;
- compatível com `aria-live` quando usado em feedback dinâmico;
- não expor dados sensíveis;
- não renderizar HTML inseguro.

Alerts usados em regiões globais devem funcionar com:

```html
<div id="global-feedback" aria-live="polite" aria-atomic="true"></div>
<div id="global-errors" aria-live="assertive" aria-atomic="true"></div>
```

Alert não deve conter stack trace, exceção técnica ou detalhe interno de backend.

Exemplo:

```django
{% include "web/components/alert.html" with variant="success" message="Solicitação criada com sucesso." %}
```

#### `form_field.html`

Propósito: renderizar campo de formulário com label, help text, erro e acessibilidade consistente.

Usar para:

- inputs Django forms;
- selects;
- textareas;
- campos com erro;
- campos com help text.

Não usar para:

- layout completo de formulário;
- fieldsets complexos;
- componentes customizados com múltiplos inputs sem contrato próprio.

Requisitos obrigatórios:

- label visível ou nome acessível;
- associação entre label e input;
- erro por campo renderizado quando existir;
- `aria-invalid` quando campo estiver inválido;
- `aria-describedby` apontando para erro e help text quando aplicável;
- help text não deve substituir label;
- estado disabled deve ser claro.

O componente pode receber um field de Django form quando isso simplificar a renderização, desde que não esconda regra de negócio nem gere markup inacessível.

Exemplo:

```django
{% include "web/components/form_field.html" with field=form.description %}
```

Quando o campo exigir layout ou comportamento especial, deve ser criada uma partial específica da jornada em vez de inflar `form_field.html`.

#### `empty_state.html`

Propósito: renderizar estado vazio consistente, com mensagem clara e action opcional.

Usar para:

- lista sem registros;
- filtro sem resultados;
- usuário sem solicitações;
- fila vazia;
- tabela sem itens.

Requisitos obrigatórios:

- título claro;
- descrição objetiva;
- action opcional quando houver próximo passo;
- não culpar o usuário;
- não esconder erro como estado vazio;
- diferenciar vazio real de falha de carregamento.

Variantes permitidas inicialmente:

- `default`;
- `filtered`;
- `permission`.

Exemplo:

```django
{% include "web/components/empty_state.html" with title="Nenhuma solicitação encontrada" description="Quando houver solicitações, elas aparecerão aqui." %}
```

#### `pagination.html`

Propósito: renderizar navegação de páginas de forma consistente e acessível.

Usar para:

- listas paginadas;
- tabelas paginadas;
- resultados filtrados.

Requisitos obrigatórios:

- navegação com semântica adequada;
- estado atual identificado;
- links anterior/próximo claros;
- disabled quando anterior/próximo não existirem;
- preservar filtros na URL;
- funcionar com HTMX quando a lista for parcial;
- não depender apenas de ícones.

Quando usado com HTMX, deve declarar target e swap de forma explícita ou seguir helper/recipe da jornada.

#### `modal_shell.html`

Propósito: fornecer estrutura acessível e consistente para modais.

Usar para:

- confirmação de action;
- formulário curto em modal;
- mensagem de conflito;
- detalhe rápido.

Não usar para:

- fluxos longos;
- formulários complexos;
- processos com muitas etapas;
- conteúdo que deveria ser página.

Requisitos obrigatórios:

- nome acessível;
- `role="dialog"` ou equivalente;
- `aria-modal` ou comportamento equivalente;
- foco inicial ao abrir;
- retorno de foco ao fechar;
- fechamento por teclado quando permitido;
- ações claras;
- não depender exclusivamente de clique fora;
- compatível com HTMX e Alpine.js.

O modal shell pode usar Alpine.js para abertura, fechamento e foco, mas não pode conter regra de negócio, autorização ou validação de domínio.

#### Política para novos componentes

Um novo include oficial só pode ser criado quando atender a pelo menos quatro critérios:

- aparece em três ou mais telas;
- possui semântica clara;
- possui variações limitadas;
- exige acessibilidade consistente;
- possui estados padronizados;
- não depende fortemente do contexto da página;
- pode ter API simples;
- sua alteração centralizada reduz manutenção.

Se o padrão for grande, contextual ou com muitos slots, deve começar como recipe documentada ou partial específica da jornada.

Não é permitido:

- criar include com muitos parâmetros para cobrir todos os casos;
- passar `request`, `user`, `model`, `object` ou `queryset` para componente genérico;
- colocar regra de permissão dentro de componente visual;
- colocar query dentro de include;
- usar include para esconder lógica de domínio;
- usar `raw_html` ou `safe` como API de componente;
- usar `onclick`, `onchange` ou scripts inline em componentes;
- criar variantes visuais locais sem documentação;
- usar `extra_classes` para contornar design system;
- criar componente novo sem propósito e contrato documentados.

O PR1 deve criar os includes oficiais iniciais com contrato fino respeitado. Não é necessário resolver todos os casos futuros, mas cada componente deve ter:

- propósito claro;
- variantes iniciais;
- requisitos de acessibilidade;
- exemplo de uso;
- teste mínimo de renderização ou cobertura por página de exemplo.

O PR1 não deve aceitar componentes com APIs extensas, parâmetros de domínio, lógica de permissão, HTML inseguro ou dependência de model inteiro.

### Direção visual

A direção visual oficial do frontend é híbrida, com base institucional sóbria, densidade operacional nas jornadas `desktop-optimized` e experiência limpa e direta nas jornadas `mobile-primary`.

A personalidade visual padrão do sistema deve transmitir:

- clareza;
- confiança;
- sobriedade institucional;
- eficiência operacional;
- baixa ornamentação;
- consistência;
- legibilidade;
- previsibilidade.

O sistema não deve adotar estética excessivamente expressiva, promocional ou "SaaS genérica". A interface deve parecer uma ferramenta operacional confiável para uso institucional, não uma landing page, dashboard de marketing ou produto visualmente performático sem necessidade.

A base visual oficial é:

- institucional sóbria como linguagem principal;
- operacional densa onde a tarefa exigir produtividade e comparação de dados;
- mobile limpo e objetivo para solicitantes e chefias.

Essa decisão orienta tokens, componentes, espaçamento, tabelas, cards, botões, badges, alerts, modais, formulários e estados de UI.

#### Base institucional sóbria

A base visual padrão deve ser usada em todo o shell, navegação, páginas administrativas, formulários, páginas de detalhe, fluxos de solicitação e aprovação.

Características obrigatórias:

- fundo principal claro;
- superfícies brancas ou neutras;
- bordas discretas;
- sombras leves ou inexistentes;
- raios moderados;
- paleta contida;
- cor primária usada com parcimônia;
- status representados por cores semânticas consistentes;
- tipografia funcional;
- layout limpo;
- espaçamento previsível.

A base institucional deve favorecer confiança, estabilidade e baixo atrito cognitivo.

#### Densidade operacional para jornadas desktop-optimized

Jornadas `desktop-optimized`, especialmente relacionadas a Almoxarifado, estoque, movimentações, filas de atendimento, inventário e materiais, podem usar maior densidade visual.

Essa densidade deve aparecer em:

- tabelas mais compactas;
- filtros mais ricos;
- toolbars funcionais;
- badges de status bem visíveis;
- ações rápidas por linha;
- maior aproveitamento horizontal;
- menor espaçamento vertical relativo;
- mais informação por viewport.

A densidade operacional não deve comprometer:

- legibilidade;
- contraste;
- foco visível;
- acessibilidade;
- clareza de status;
- área mínima de clique;
- entendimento das ações críticas.

A densidade operacional deve ser aplicada por necessidade da jornada, não como estética global.

#### Mobile limpo para solicitantes e chefias

Jornadas `mobile-primary`, especialmente `nova solicitação`, `minhas solicitações`, detalhe de solicitação, aprovação e acompanhamento de status, devem usar layout limpo e direto.

O mobile deve priorizar:

- uma tarefa principal por tela;
- cards/listas simples;
- ações primárias visíveis;
- textos objetivos;
- baixo volume de informação simultânea;
- formulários de uma coluna;
- status claros;
- feedback explícito;
- poucos filtros;
- mínima carga cognitiva.

No mobile, não se deve replicar a densidade das telas de Almoxarifado desktop. Quando uma tabela desktop for necessária, o mobile deve usar representação simplificada, como cards ou lista com campos prioritários.

#### Tokens visuais iniciais

Os tokens iniciais devem refletir neutralidade institucional e estados semânticos consistentes.

A paleta base deve usar:

- neutros para fundo, superfície, borda e texto;
- uma cor primária institucional para ações principais;
- cores semânticas para status e feedback;
- baixo uso de cores ornamentais.

Categorias obrigatórias de tokens:

- `surface`;
- `surface-muted`;
- `surface-raised`;
- `border`;
- `border-strong`;
- `text-primary`;
- `text-secondary`;
- `text-muted`;
- `brand`;
- `brand-hover`;
- `brand-subtle`;
- `success`;
- `warning`;
- `danger`;
- `info`;
- `focus-ring`.

As cores semânticas representam significado consistente em todo o sistema:

- `success`: concluído, aprovado, disponível;
- `warning`: pendente, atenção, aguardando ação;
- `danger`: erro, rejeitado, bloqueado, ação destrutiva;
- `info`: informação, status neutro, orientação;
- `brand`: ação primária e navegação ativa.

Não é permitido criar novas cores de status em páginas específicas sem atualizar os tokens e a documentação do design system.

#### Bordas, raios e sombras

A interface deve usar bordas discretas como principal separador visual. Sombras devem ser leves e usadas com parcimônia. Raios devem ser moderados. O sistema não deve usar cantos excessivamente arredondados como linguagem dominante.

Diretrizes:

- cards e painéis: borda discreta, sombra leve ou nenhuma sombra;
- botões e inputs: raio moderado;
- modais: sombra mais perceptível, mas não decorativa;
- tabelas: separação por borda/linha, não por cards pesados;
- badges: raio moderado ou pill quando status exigir destaque.

#### Componentes visuais

Botões devem ser funcionais, consistentes e pouco ornamentados.

Variações oficiais de botão:

- `primary`;
- `secondary`;
- `outline`;
- `ghost`;
- `danger`.

Botões primários devem ser usados apenas para a ação principal da tela ou do contexto. Não deve haver múltiplos botões primários concorrendo visualmente na mesma área.

Badges devem ser semânticas e consistentes. Status iguais devem ter a mesma aparência em todo o sistema.

Alerts devem ser claros, textuais e sem excesso visual. A cor deve reforçar o significado, mas a mensagem textual deve ser suficiente para entendimento.

Cards devem ser usados para agrupamento, não como decoração. Em desktop operacional, cards não devem substituir tabelas quando a tarefa exigir comparação de dados.

Tabelas são componente operacional essencial. Devem priorizar:

- legibilidade;
- alinhamento;
- status visíveis;
- ações por linha claras;
- empty state consistente;
- paginação previsível;
- filtros acessíveis;
- densidade apropriada à jornada.

#### Tipografia

A tipografia deve ser funcional e hierárquica, sem excesso de variações.

A escala tipográfica deve diferenciar claramente:

- título de página;
- subtítulo/descrição;
- título de seção;
- texto de corpo;
- texto secundário;
- label;
- helper text;
- mensagem de erro;
- texto de tabela;
- badge/status.

Não é permitido criar tamanhos arbitrários de texto em cada página. A escala tipográfica deve seguir os tokens e recipes definidos no design system.

#### Movimento e animação

Movimento deve ser mínimo, funcional e não ornamental.

Animações são permitidas apenas quando ajudarem a comunicar:

- abertura/fechamento de modal;
- dropdown;
- drawer mobile;
- loading;
- transição leve de feedback.

Não devem ser usadas animações para embelezar dashboards, cards ou ações sem necessidade operacional.

#### Responsividade visual

A direção visual deve respeitar a classificação responsiva da jornada:

- `mobile-primary`: limpo, direto, baixa densidade;
- `desktop-optimized`: denso, tabular, produtivo;
- `responsive-neutral`: institucional padrão.

Agentes devem definir a categoria responsiva da jornada antes de aplicar padrões visuais.

#### Padrões proibidos

Não é permitido:

- criar paleta local por página;
- usar cores fora dos tokens sem decisão documentada;
- usar gradientes decorativos como padrão;
- usar sombras fortes em cards comuns;
- usar cards decorativos para substituir tabelas operacionais;
- usar múltiplos botões primários concorrentes no mesmo contexto;
- usar status com cores inconsistentes entre telas;
- usar bordas, raios ou espaçamentos arbitrários sem recipe;
- criar estilo visual "SaaS marketing" para telas operacionais;
- usar animações ornamentais;
- usar ícones decorativos sem função;
- usar densidade desktop em jornada `mobile-primary`;
- usar layout mobile simplificado demais em jornada operacional `desktop-optimized`.

Ao implementar uma nova tela, agentes devem primeiro identificar a categoria da jornada e aplicar a direção visual correspondente:

- `mobile-primary`: interface limpa, cards/listas simples, baixa densidade, ação principal evidente;
- `desktop-optimized`: tabelas, filtros, status, densidade operacional e uso eficiente de tela;
- `responsive-neutral`: base institucional sóbria.

Agentes não devem inventar novas cores, novos estilos de botão, novos padrões de badge, novos raios, novas sombras ou novas densidades sem atualizar a documentação do design system.

Qualquer novo padrão visual deve ser tratado como alteração de design system, não como decisão local de página.

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

### Camada de apresentação

O projeto usa uma camada de apresentação híbrida entre apps de domínio e `apps/web`.

Apps de domínio devem expor selectors, policies, forms, services e pequenos context builders/presenters para traduzir dados de domínio em dados simples de UI.

Esses context builders/presenters podem preparar:

- labels;
- variantes visuais de status, como `status_variant`;
- booleans de ação, como `can_cancel`, `can_authorize` e equivalentes;
- URLs de actions;
- textos de empty state;
- listas paginadas já filtradas e autorizadas;
- mensagens de feedback de domínio seguras para apresentação;
- metadados mínimos para templates e partials.

`apps/web` deve compor página, shell, layout, templates e partials. Não deve calcular status visual, permissão, queryset complexa, regra operacional ou decisão de workflow.

Views em `apps/web` devem chamar context builders/presenters dos apps de domínio e renderizar o template ou partial apropriado. Se uma view precisar conhecer regra de domínio para montar a resposta, essa regra deve ser movida para o app de domínio correspondente.

Includes do design system recebem dados simples já preparados. Eles não recebem `request`, `user`, `model`, `object`, `queryset`, `policy` ou permissão bruta para decidir comportamento.

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

### Autenticação HTML

O fluxo de autenticação do frontend server-rendered deve ser implementado com views HTML próprias em `apps/web`, usando sessão Django, templates server-rendered e formulários HTML convencionais, com suporte a HTMX apenas quando agregar valor à experiência.

Login, logout e telas relacionadas à autenticação fazem parte da experiência HTML do app e devem seguir os mesmos padrões de shell, segurança, acessibilidade, Tailwind CSS, HTMX e testes de contrato definidos para o frontend server-rendered.

APIs de autenticação existentes ou futuras podem continuar existindo para contratos externos, integrações, mobile app futuro ou automações, mas não devem ser a base primária do login HTML do app server-rendered.

Views HTML de autenticação devem ficar em:

- `apps/web/views/auth.py`.

Templates devem ficar em:

- `apps/web/templates/web/pages/auth/`.

Estrutura recomendada:

```text
apps/web/templates/web/pages/auth/
  login.html
  logged_out.html
  password_reset_request.html
  password_reset_done.html
  password_reset_confirm.html
  password_reset_complete.html
```

Caso o projeto use shell específico para páginas públicas de autenticação, ele deve ficar em:

- `apps/web/templates/web/layouts/auth_shell.html`.

O shell autenticado principal continua separado:

- `apps/web/templates/web/layouts/app_shell.html`.

A autenticação deve usar formulários Django, validações Django e sessão Django. Regras de domínio, policies ou serviços de usuário devem permanecer no app de domínio responsável, como `apps/users`, quando houver lógica específica de usuário, auditoria, bloqueio, perfil, papel ou permissão.

Exemplo de separação esperada:

```text
apps/web/
  views/auth.py
  templates/web/pages/auth/
  templates/web/layouts/auth_shell.html
apps/users/
  services.py
  policies.py
  selectors.py
  forms.py
```

`apps/web` pode orquestrar o fluxo visual e chamar services/policies de `apps/users`, mas não deve concentrar regra de negócio de usuário.

#### Login

O login do app HTML deve ser uma view server-rendered.

A view deve:

- renderizar template HTML;
- usar formulário Django;
- validar credenciais no backend;
- criar sessão Django em caso de sucesso;
- redirecionar para rota interna segura;
- renderizar erros de formulário em caso de falha;
- respeitar o contrato de acessibilidade de formulários;
- respeitar CSRF;
- não expor motivo sensível de falha.

O login pode aceitar submit convencional HTML como comportamento base.

HTMX pode ser usado para melhorar a experiência, por exemplo renderizar erros sem reload completo, mas não deve ser obrigatório para o funcionamento do login. O fluxo de login deve funcionar corretamente sem JavaScript.

#### Logout

O logout deve ser uma view HTML/server-rendered, usando sessão Django.

O logout deve:

- exigir método seguro conforme política do projeto, preferencialmente `POST`;
- usar CSRF quando for `POST`;
- encerrar a sessão no backend;
- redirecionar para tela pública apropriada;
- não depender de HTMX;
- não depender de chamada a API JSON para funcionar.

Logout via link `GET` deve ser evitado. A action de logout deve preferencialmente ser um formulário `POST` estilizado como item de menu/botão, seguindo o componente oficial de botão/link de action quando aplicável.

#### Integração com APIs existentes

Endpoints DRF ou API-first de autenticação não devem ser consumidos diretamente pelo formulário HTML de login via HTMX como padrão.

Não é recomendado que a tela HTML de login chame uma API JSON e depois converta erros JSON para fragments HTML, porque isso mistura contratos diferentes:

- contrato HTML server-rendered;
- contrato JSON/API;
- contrato HTMX fragmentado;
- contrato de sessão Django.

Essa mistura aumenta complexidade, dificulta tratamento de erro, cria duplicação de mapeamento de mensagens, prejudica acessibilidade e gera ambiguidade para agentes de IA.

APIs de autenticação podem continuar existindo para:

- clientes externos;
- mobile app futuro;
- integrações;
- testes de contrato API;
- uso administrativo específico;
- evolução futura.

Mas o frontend server-rendered deve usar views HTML próprias.

#### HTMX em autenticação

HTMX pode ser usado no fluxo de autenticação apenas de forma progressiva.

Usos permitidos:

- renderizar erros de login na própria área do formulário;
- atualizar partial de mensagens;
- validar trecho específico de formulário quando fizer sentido;
- mostrar feedback acessível sem reload completo.

Usos proibidos:

- login depender exclusivamente de HTMX;
- misturar envelope JSON de API com partial HTML;
- injetar página de login dentro de modal ou target operacional;
- retornar login HTML como resposta a uma action HTMX autenticada expirada;
- usar HTMX para contornar fluxo normal de sessão.

Se uma request HTMX autenticada expirar durante uso do app, o comportamento deve seguir o contrato global HTMX:

- retornar `401`;
- usar `HX-Redirect` para a tela de login ou `HX-Refresh` quando aplicável;
- não renderizar login dentro de partial operacional.

#### Segurança da autenticação

O fluxo HTML de autenticação deve seguir as políticas de segurança frontend já definidas.

Obrigatório:

- CSRF em formulários de login/logout quando aplicável;
- escape padrão Django;
- não usar scripts inline soltos;
- não usar handlers nativos como `onclick`, `onchange` e `onload`;
- não expor dados sensíveis no HTML;
- não revelar se usuário existe ou não em mensagens de erro;
- validar redirects internos;
- não confiar em `next` sem validação;
- não autenticar ou autorizar no frontend;
- não armazenar token sensível no DOM.

Parâmetros de redirecionamento, como `next`, só podem ser usados quando forem validados como URLs internas seguras. Não é permitido redirecionar para domínio externo a partir do fluxo de login/logout.

Mensagens de erro de login devem ser genéricas, por exemplo:

```text
Credenciais inválidas.
```

Não devem diferenciar publicamente:

- usuário inexistente;
- senha incorreta;
- usuário inativo;
- permissão insuficiente.

Quando houver necessidade administrativa de diagnóstico, isso deve ser registrado em log server-side, não exposto ao usuário final.

#### Acessibilidade da autenticação

As telas de autenticação devem seguir o contrato obrigatório de acessibilidade.

O formulário de login deve garantir:

- label visível para cada campo;
- mensagens de erro associadas semanticamente;
- `aria-invalid` em campos inválidos quando aplicável;
- `aria-describedby` ligando campo ao erro/help text;
- erro global acessível;
- foco adequado após falha de validação;
- botão submit com `type` explícito;
- estado loading/disabled quando usado com HTMX;
- funcionamento por teclado;
- contraste adequado.

A tela de login deve ter estrutura clara, sem depender de layout do shell autenticado.

O shell de autenticação deve ser simples e não deve expor navegação operacional do sistema para usuários não autenticados.

#### Design system da autenticação

As telas de autenticação devem seguir a direção visual oficial:

- institucional sóbria;
- baixo ruído visual;
- clareza;
- confiança;
- pouca ornamentação.

Não devem parecer landing page promocional, tela SaaS genérica ou interface visualmente desconectada do restante do sistema.

O formulário deve usar componentes oficiais sempre que possível:

- `form_field.html`;
- `button.html`;
- `alert.html`.

Não é permitido criar estilos locais para login que contradigam tokens, recipes, botões, campos ou alerts do design system.

#### Testes mínimos de autenticação

O fluxo HTML de autenticação deve ter testes com Django test client e assertions HTML.

Testes obrigatórios para login:

- `GET` login retorna `200`;
- template correto é usado;
- formulário contém CSRF;
- campos obrigatórios estão presentes;
- labels estão presentes;
- botão submit tem `type` explícito;
- credenciais inválidas retornam erro acessível;
- credenciais válidas criam sessão;
- credenciais válidas redirecionam para rota interna esperada;
- `next` interno válido é respeitado;
- `next` externo ou inseguro é ignorado ou rejeitado;
- usuário autenticado acessando login é redirecionado conforme política do projeto.

Testes obrigatórios para logout:

- logout encerra sessão;
- logout exige método definido pela política do projeto;
- logout `POST` usa CSRF;
- logout redireciona para rota pública esperada;
- usuário não autenticado recebe comportamento seguro e previsível.

Se login usar HTMX para erros de formulário, testes adicionais obrigatórios:

- `POST` HTMX inválido retorna partial/form com erro acessível;
- status de erro segue contrato definido para validação;
- não retorna JSON para tela HTML;
- não injeta shell completo dentro de partial.

Padrões proibidos:

- usar apenas API JSON para login HTML;
- fazer formulário HTML chamar endpoint DRF auth via HTMX como padrão;
- misturar erros JSON com partial HTML sem decisão explícita;
- guardar token de autenticação no DOM;
- implementar autorização no Alpine.js;
- implementar login dependente de JavaScript;
- renderizar login dentro de partial operacional após sessão expirada;
- usar redirect externo em `next`;
- criar layout visual paralelo ao design system;
- criar scripts inline específicos para login;
- expor mensagens de erro sensíveis;
- usar `GET` para logout sem decisão explícita.

Agentes devem implementar autenticação HTML dentro de `apps/web`, usando views server-rendered e templates oficiais.

Ao implementar ou alterar login/logout, agentes devem seguir estes critérios:

- view HTML em `apps/web`;
- template em `apps/web/templates/web/pages/auth/`;
- `auth_shell` quando aplicável;
- form Django;
- CSRF;
- session login/logout;
- redirect interno validado;
- componentes oficiais;
- acessibilidade obrigatória;
- testes de contrato HTML;
- sem dependência obrigatória de HTMX;
- sem consumo direto de API JSON como padrão.

Se uma API de autenticação já existir, agentes não devem reaproveitá-la automaticamente para o login HTML. O reaproveitamento correto deve ocorrer no nível de services, policies ou validações compartilhadas, não misturando contratos de transporte.

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

### URLs HTML

Rotas HTML server-rendered do piloto vivem em `apps/web/urls.py` com `app_name = "web"`.

Nomes de rotas devem ser estáveis e seguir o namespace único `web`:

- `web:login`;
- `web:logout`;
- `web:home`;
- `web:requisitions_mine`;
- `web:requisition_create`;
- `web:requisition_detail`;
- `web:authorizations_list`;
- `web:fulfillments_list`.

Partials e actions HTMX devem seguir o padrão `web:<jornada>_<acao>`.

Templates, views e context builders devem usar `reverse()` ou a tag `{% url %}`. Não é permitido hardcode de path quando houver rota nomeada.

### Navegação principal

A navegação principal do app deve ser baseada em allowlist por papel operacional principal, montada no backend por um context builder de navegação, e renderizada pelo template sem lógica de autorização complexa.

O menu não deve ser montado diretamente no template por inspeção de permissões, roles ou condições de domínio. O template deve receber uma estrutura de navegação já resolvida, contendo apenas os itens que o usuário atual pode visualizar.

O objetivo é manter a navegação previsível, auditável e clara para agentes de IA, evitando templates cheios de condicionais como:

```django
{% if user.is_superuser %}
{% if perms.requisitions.can_approve %}
{% if request.user.profile.role == "warehouse" %}
{% if some_policy_check %}
```

A regra correta é: o backend decide quais itens existem; o template apenas renderiza.

#### Responsabilidade por camada

A montagem da navegação deve ficar em um context builder dedicado, por exemplo:

- `apps/web/navigation.py`;
- `apps/web/context/navigation.py`.

Esse módulo deve expor função clara, por exemplo:

- `build_navigation_for_user(user)`;
- `get_navigation_context(request)`.

A função deve retornar uma estrutura simples e serializável para o template, contendo grupos, itens, URLs, labels, ícones opcionais, estado ativo e metadados mínimos de apresentação.

Exemplo conceitual:

```python
[
    {
        "label": "Solicitações",
        "items": [
            {
                "label": "Minhas solicitações",
                "url": "/solicitacoes/minhas/",
                "active": True,
                "icon": "clipboard-list",
            },
            {
                "label": "Nova solicitação",
                "url": "/solicitacoes/nova/",
                "active": False,
                "icon": "plus",
            },
        ],
    },
]
```

O template do shell deve apenas iterar sobre essa estrutura:

```django
{% for group in navigation %}
  {% for item in group.items %}
    ...
  {% endfor %}
{% endfor %}
```

O template não deve decidir se o item aparece com base em permissão, papel, status ou regra de negócio.

#### Papel operacional principal

A navegação deve ser orientada pelo papel operacional principal do usuário, não pela estrutura técnica dos apps Django.

Papéis operacionais iniciais esperados:

- solicitante;
- chefia;
- almoxarifado;
- admin.

A nomenclatura final pode ser ajustada conforme o domínio, mas a navegação deve refletir tarefas reais do usuário, não nomes técnicos como `requisitions`, `stock`, `users` ou `materials`.

Exemplo de navegação por papel:

```text
Solicitante
  Nova solicitação
  Minhas solicitações
Chefia
  Aprovações pendentes
  Histórico de aprovações
Almoxarifado
  Fila de atendimento
  Estoque
  Movimentações
  Materiais
Admin
  Usuários
  Permissões
  Configurações
```

Um usuário com múltiplas capacidades pode receber uma navegação combinada, mas essa combinação deve ser resolvida no context builder, não no template.

#### Allowlist por papel

A navegação deve ser construída por allowlist.

Cada papel operacional deve ter uma lista explícita de itens de menu permitidos.

Exemplo conceitual:

```python
NAVIGATION_BY_ROLE = {
    "requester": [
        "requisitions.mine",
        "requisitions.create",
    ],
    "manager": [
        "approvals.pending",
        "approvals.history",
    ],
    "warehouse": [
        "warehouse.queue",
        "stock.list",
        "movements.list",
        "materials.list",
    ],
    "admin": [
        "users.list",
        "permissions.list",
        "settings.index",
    ],
}
```

A allowlist define visibilidade de navegação, não autorização final.

Mesmo que um item apareça no menu, cada view e cada action HTMX ainda deve validar permissão no backend.

A navegação não deve ser tratada como mecanismo de segurança. Ela é apenas uma camada de UX.

#### Separação entre navegação e autorização

A navegação deve usar permissões/policies apenas para decidir visibilidade de itens, mas não deve substituir autorização nas views.

Obrigatório:

- views protegidas por autenticação;
- views protegidas por permissão/policy quando aplicável;
- actions HTMX protegidas por permissão/policy;
- `POST`, `PUT`, `PATCH` e `DELETE` sempre validam autorização no backend;
- menu não é fonte de verdade de segurança.

Proibido:

- esconder item no menu e considerar a rota protegida;
- autorizar action apenas porque o menu exibiu o item;
- validar permissão apenas no template;
- passar policies complexas para o template;
- decidir autorização com Alpine.js;
- decidir autorização com HTMX no frontend.

#### Context builder de navegação

O context builder deve ser o ponto único de montagem da navegação.

Ele deve ser responsável por:

- identificar usuário atual;
- identificar papel operacional principal;
- combinar itens quando usuário tiver múltiplos papéis;
- remover itens não permitidos;
- resolver URLs;
- marcar item ativo;
- agrupar itens;
- ordenar grupos e itens;
- retornar estrutura simples para template.

Ele não deve:

- executar queries pesadas;
- carregar contadores caros sem cache ou decisão explícita;
- executar lógica de domínio complexa;
- retornar models inteiros;
- retornar objetos de permissão brutos;
- retornar dados sensíveis;
- depender de estado de UI.

Se algum item precisar de contador, badge ou indicador, isso deve ser documentado separadamente e tratado como dado de navegação opcional, com cuidado de performance.

Exemplo:

```python
{
    "label": "Aprovações pendentes",
    "url": "/aprovacoes/",
    "active": False,
    "badge": {
        "label": "3",
        "variant": "warning",
    },
}
```

Contadores não devem ser adicionados por padrão. Eles só devem existir quando forem relevantes para a tarefa e baratos ou otimizados.

#### Estado ativo

O estado ativo do menu deve ser resolvido pelo backend ou por regra simples no context builder.

O template deve receber:

```python
"active": True
```

ou equivalente.

O template não deve conter lógica complexa para comparar paths, nomes de rotas, namespaces ou múltiplas condições.

Se necessário, cada item pode declarar nomes de rotas associadas:

```python
"active_routes": ["requisitions:list", "requisitions:detail"]
```

mas a resolução final ainda deve ocorrer no builder.

#### Shell mobile e desktop

A mesma estrutura de navegação deve alimentar:

- sidebar desktop;
- drawer/menu mobile;
- atalhos de navegação quando aplicável.

Não devem existir duas árvores de navegação independentes para mobile e desktop.

A diferença entre desktop e mobile deve ser apenas de apresentação.

O shell pode renderizar a mesma allowlist em formatos diferentes:

- desktop: sidebar;
- mobile: drawer/header menu.

Mas os itens, labels, permissões e ordem devem vir da mesma fonte.

#### Labels e linguagem

Labels do menu devem ser orientados a tarefas, não a termos técnicos.

Preferir:

- Minhas solicitações;
- Nova solicitação;
- Aprovações pendentes;
- Fila de atendimento;
- Movimentações;
- Usuários.

Evitar:

- Requisitions;
- Stock;
- Users app;
- Materials module;
- Admin area.

A navegação deve usar a linguagem do usuário final e do domínio operacional.

#### Design system e acessibilidade

O menu deve seguir o design system oficial.

Obrigatório:

- item ativo visualmente claro;
- estado hover/focus visível;
- suporte a teclado;
- labels textuais acessíveis;
- ícones apenas decorativos ou com nome acessível quando necessários;
- drawer mobile acessível;
- foco controlado no menu mobile;
- não depender de hover;
- contraste adequado.

Ícones não devem substituir texto no menu principal.

Se ícones forem usados, devem reforçar o reconhecimento visual, não carregar o significado sozinhos.

#### Testes mínimos de navegação

A navegação deve ter testes de contrato com Django test client.

Testes obrigatórios:

- usuário solicitante vê apenas itens de solicitante;
- usuário chefia vê itens de aprovação esperados;
- usuário almoxarifado vê itens operacionais esperados;
- usuário admin vê itens administrativos esperados;
- usuário sem permissão não vê item restrito;
- template renderiza navegação recebida sem lógica de permissão;
- item ativo é marcado corretamente;
- sidebar desktop usa a estrutura de navegação;
- menu mobile usa a mesma estrutura de navegação;
- rota protegida continua bloqueada mesmo se acessada diretamente.

Quando usuário tiver múltiplos papéis, deve haver teste específico para a composição de navegação esperada.

#### Padrões proibidos de navegação

Não é permitido:

- montar menu diretamente no template com condicionais de permissão;
- espalhar lógica de navegação por múltiplos templates;
- duplicar árvore de navegação para mobile e desktop;
- basear menu na estrutura técnica dos apps Django;
- usar menu como mecanismo de segurança;
- passar `request.user` para includes de menu decidirem autorização;
- passar objetos de policy para template;
- executar queries pesadas durante renderização do menu;
- criar item de menu local em uma página sem registrar no builder;
- criar labels inconsistentes entre papéis;
- criar item de menu sem rota nomeada ou URL resolvida.

#### Critério para agentes de IA

Agentes de IA devem criar ou alterar itens de navegação exclusivamente no context builder de navegação.

Ao adicionar uma nova jornada, o agente deve:

- definir qual papel operacional acessa a jornada;
- registrar o item na allowlist do papel correspondente;
- definir label orientado à tarefa;
- definir URL ou route name;
- definir grupo de navegação;
- definir regra de active state;
- garantir que a view tenha proteção de permissão própria;
- atualizar testes de navegação.

Agentes não devem adicionar links de menu diretamente no shell, em partials de jornada ou em templates de domínio.

Se uma nova jornada não se encaixar em nenhum papel operacional existente, o agente deve registrar uma lacuna de produto/arquitetura em vez de criar um grupo ou papel novo silenciosamente.

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

Lookups operacionais do frontend server-rendered usam HTMX server-rendered por padrão.

Regras:

- endpoint retorna partial HTML, não JSON, para tela server-rendered;
- mínimo de 3 caracteres;
- resultado curto;
- só entidades ativas e autorizadas;
- sem dados sensíveis extras no DOM;
- empty, loading e error states explícitos;
- teclado e leitor de tela suportados;
- Alpine.js pode apenas controlar disclosure/seleção visual local.

Lookups não devem virar mini-SPA em Alpine.js. Quando uma API JSON existir para outro contrato, o frontend HTML não deve consumi-la automaticamente se isso exigir duplicar estado, validação ou apresentação no cliente.

## 9. Sequência de reconstrução e delivery

A implementação do frontend server-rendered deve seguir uma estratégia híbrida em 2 PRs iniciais, combinando uma fundação mínima antes das jornadas com uma primeira jornada real usada para validar e ajustar os padrões.

Não é permitido iniciar diretamente por uma jornada funcional, como `Minhas solicitações`, antes de existir uma base mínima compartilhada de shell, Tailwind CSS, HTMX, Alpine.js, componentes iniciais e testes de contrato. Também não é desejável criar uma fundação extensa e abstrata sem validar os padrões em uma jornada real.

A decisão oficial de delivery é:

1. PR1 cria a fundação mínima compartilhada.
2. PR2 implementa a primeira jornada real `mobile-primary` usando essa fundação.
3. Jornadas seguintes evoluem incrementalmente sem reabrir arquitetura, salvo decisão explícita documentada.

### PR1 — Fundação mínima do frontend server-rendered

O primeiro PR deve criar apenas a base necessária para permitir que agentes implementem jornadas futuras sem reabrir decisões estruturais. Esse PR não deve implementar fluxo operacional completo.

O PR1 deve conter obrigatoriamente:

```text
apps/web/
  urls.py
  views/
  templates/
  static/
```

A estrutura mínima de templates deve ser criada em:

```text
apps/web/templates/web/
  layouts/
  components/
  partials/
  pages/
```

O shell base deve ser criado com:

- `apps/web/templates/web/layouts/base.html`;
- `apps/web/templates/web/layouts/app_shell.html`.

O shell deve conter:

- header;
- navegação por papel/permissão em estrutura inicial;
- sidebar desktop;
- drawer/menu mobile;
- área global de feedback;
- área global de erros;
- modal root;
- container principal de página;
- carregamento do CSS compilado;
- bootstrap de Alpine.js/HTMX quando aplicável.

O Tailwind CSS deve ser configurado em modo CSS-first com os arquivos oficiais:

- `apps/web/static/web/src/styles.css`;
- `apps/web/static/web/dist/app.css`.

O arquivo `styles.css` deve conter:

- `@import "tailwindcss"`;
- `@source` apontando para templates Django autorizados;
- `@theme` com tokens visuais iniciais;
- recipes/utilitários mínimos e documentados.

O CSS compilado não deve ser editado manualmente.

O PR1 deve incluir os scripts oficiais de build/watch do CSS:

```json
{
  "scripts": {
    "css:dev": "tailwindcss -i apps/web/static/web/src/styles.css -o apps/web/static/web/dist/app.css --watch",
    "css:build": "tailwindcss -i apps/web/static/web/src/styles.css -o apps/web/static/web/dist/app.css --minify"
  }
}
```

O PR1 deve criar os componentes iniciais mínimos em `apps/web/templates/web/components/`:

- `button.html`;
- `badge.html`;
- `alert.html`;
- `form_field.html`;
- `empty_state.html`;
- `pagination.html`;
- `modal_shell.html`.

Esses componentes devem ser simples, acessíveis e com API pequena. Não devem conter regra de negócio, queries, permissões, cálculos de workflow ou lógica de domínio.

O PR1 deve criar helpers mínimos para respostas HTMX, preferencialmente em `apps/web/htmx.py`.

Helpers mínimos:

- render de partial HTMX;
- `HX-Redirect`;
- `HX-Refresh`;
- `HX-Trigger`;
- `HX-Retarget`;
- resposta de validação `422`;
- resposta de permissão `403`;
- resposta de conflito `409`;
- resposta de sessão expirada `401`.

O PR1 deve estabelecer targets globais oficiais no shell:

```html
<div id="global-feedback" aria-live="polite" aria-atomic="true"></div>
<div id="global-errors" aria-live="assertive" aria-atomic="true"></div>
<div id="modal-root"></div>
```

O PR1 deve definir o bootstrap mínimo de segurança frontend:

- CSRF disponível para requests HTMX mutáveis;
- proibição de scripts inline soltos;
- proibição de handlers nativos como `onclick`, `onchange` e `onload`;
- uso de escape padrão do Django;
- uso de `json_script` para JSON seguro;
- não uso de Tailwind CDN.

O PR1 deve criar pelo menos uma página técnica simples para validar shell e assets, por exemplo `apps/web/templates/web/pages/home.html`. Essa página não deve ser considerada uma jornada operacional. Ela serve apenas para validar layout, build CSS, navegação inicial, feedback regions, modal root e carregamento de assets.

O PR1 deve incluir testes mínimos de contrato para a fundação:

- `GET` da página base retorna `200`;
- template correto é usado;
- CSS compilado é referenciado no shell;
- targets globais existem;
- regiões `aria-live` existem;
- `modal-root` existe;
- navegação base é renderizada;
- componentes principais podem ser renderizados;
- CSRF/HTMX base está configurado quando aplicável.

O PR1 não deve conter:

- fluxo operacional completo;
- regras de negócio em `apps/web`;
- queries complexas em views de `web`;
- templates em `apps/<domain>/templates/`;
- layout paralelo;
- Tailwind CDN;
- scripts inline soltos;
- componentes genéricos complexos;
- abstrações prematuras de tabela, dashboard ou workflow.

### PR2 — Primeira jornada real usando a fundação

O segundo PR deve implementar a primeira jornada real usando a fundação criada no PR1. A jornada recomendada para o PR2 deve ser `mobile-primary`, preferencialmente `Minhas solicitações`.

Essa jornada deve validar shell, navegação por papel, layout responsivo, listas/cards mobile, empty state, permissões simples, partials HTMX e testes de contrato sem começar pela operação mais densa do Almoxarifado.

O PR2 deve implementar a jornada dentro da estrutura oficial:

```text
apps/web/templates/web/pages/<jornada>/
```

Exemplo:

```text
apps/web/templates/web/pages/requisitions/
  list.html
  _list.html
  _filters.html
  _empty_state.html
```

As views que renderizam páginas e partials devem ficar em `apps/web/views/`.

Regras de domínio, consultas, permissões, forms e context builders devem permanecer nos apps de domínio correspondentes, por exemplo:

- `apps/requisitions/selectors.py`;
- `apps/requisitions/services.py`;
- `apps/requisitions/policies.py`;
- `apps/requisitions/forms.py`;
- `apps/requisitions/context.py`.

O PR2 deve validar e ajustar os padrões criados no PR1, mas não deve reabrir a arquitetura salvo se houver bloqueio real.

Ajustes permitidos:

- refinar recipes de layout;
- ajustar tokens visuais iniciais;
- melhorar componente existente;
- adicionar partial específica da jornada;
- adicionar helper HTMX pequeno e genérico;
- corrigir lacuna de acessibilidade;
- corrigir lacuna de teste.

Ajustes que exigem decisão explícita antes de implementação:

- criar novo shell;
- mudar estrutura física de templates;
- criar templates em apps de domínio;
- introduzir nova toolchain de build;
- criar componente genérico complexo;
- mudar contrato HTMX global;
- mudar política de Tailwind;
- mudar política de segurança frontend.

O PR2 deve incluir testes mínimos de contrato da jornada:

- `GET` da página por usuário autorizado retorna `200`;
- template de página correto é usado;
- targets HTMX da jornada existem;
- estado vazio é renderizado quando não há dados;
- lista é renderizada quando há dados;
- ações aparecem conforme permissão;
- ações proibidas não aparecem para usuário sem permissão;
- request HTMX retorna partial correta;
- headers HTMX esperados são retornados quando aplicável;
- validação `422` é testada quando houver formulário;
- permissão `403` é testada em endpoint HTMX;
- sessão expirada `401` com `HX-Redirect` ou `HX-Refresh` é testada quando aplicável;
- conflito `409` é testado quando a action depender de estado de domínio;
- atributos básicos de acessibilidade são verificados.

Se a jornada usar HTMX, cada action deve declarar:

- partial renderizado;
- target esperado;
- swap esperado;
- status HTTP esperado;
- headers HTMX utilizados;
- evento emitido, quando aplicável;
- comportamento de sucesso;
- comportamento de erro;
- teste mínimo associado.

Se a jornada usar Alpine.js, o uso deve ser limitado a comportamento local de UI, como:

- abrir/fechar menu;
- abrir/fechar modal;
- toggle visual;
- filtro visual simples;
- loading local;
- estado transitório de seleção.

Alpine.js não deve conter regra de negócio, permissão, validação de domínio ou lógica de workflow.

### Ordem após PR1 e PR2

Após a fundação mínima e a primeira jornada real, as próximas entregas devem seguir ordem orientada a risco e aprendizado:

1. Jornada `mobile-primary` simples para consolidar shell e responsividade.
2. Jornada com formulário HTMX e validação `422`.
3. Jornada com aprovação/rejeição e permissão `403`.
4. Jornada com conflito de domínio `409`.
5. Jornada `desktop-optimized` de Almoxarifado com tabela, filtros e densidade operacional.
6. Fluxos críticos com Playwright antes de gate de lançamento.

A implementação de jornadas `desktop-optimized` do Almoxarifado não deve começar antes de os padrões mínimos de shell, Tailwind, HTMX, componentes, segurança, acessibilidade e testes de contrato estarem funcionando em pelo menos uma jornada real.

### Critério de aceite para iniciar novas jornadas

Uma nova jornada só pode ser iniciada por agentes de IA quando existirem:

- estrutura `apps/web` criada;
- shell base funcional;
- Tailwind build funcional;
- tokens iniciais definidos;
- componentes mínimos disponíveis;
- helpers HTMX mínimos disponíveis;
- contrato HTMX documentado;
- política de segurança frontend documentada;
- contrato de acessibilidade documentado;
- testes mínimos de fundação passando;
- exemplo de primeira jornada implementado ou em progresso controlado.

Agentes de IA devem seguir a fundação existente. Não devem criar fundação paralela dentro de uma jornada específica.

### Política de não reabrir arquitetura durante jornada

Durante a implementação de uma jornada, agentes devem tratar as seguintes decisões como já fechadas:

- `apps/web` como dono da composição visual;
- templates de página em `apps/web/templates/web/pages/<jornada>/`;
- componentes compartilhados em `apps/web/templates/web/components/`;
- Tailwind CSS v4 CSS-first;
- HTMX com contrato global mínimo;
- Alpine.js apenas para comportamento local;
- acessibilidade como contrato obrigatório;
- segurança frontend com secure defaults pragmáticos;
- testes Django client + HTML/HTMX assertions como mínimo obrigatório;
- Playwright apenas para fluxo crítico ou gate de lançamento.

Caso uma jornada exponha uma lacuna real nessas decisões, o agente deve registrar a lacuna e propor uma decisão arquitetural explícita, em vez de criar exceção silenciosa.

### Política de PRs

PRs de fundação e jornadas devem ser pequenos o suficiente para revisão objetiva.

O PR1 deve ser aceito apenas se entregar a fundação mínima funcionando, sem tentar resolver todas as jornadas futuras.

O PR2 deve ser aceito apenas se provar que a fundação suporta uma jornada real sem criar padrões paralelos.

Toda jornada posterior deve seguir o padrão:

- página completa;
- partials HTMX necessárias;
- context builder/service/selector/policy no domínio;
- componentes oficiais reaproveitados;
- testes de contrato;
- ajustes documentados de recipe quando necessário.

Não é permitido que cada jornada crie sua própria fundação privada de layout, componentes, helpers HTMX, estilos Tailwind, scripts Alpine ou padrões de teste.

### Frontend Handoff Contract

Toda issue ou PR de frontend deve declarar um contrato de handoff obrigatório antes da implementação, usando bloco padrão. Essa regra vale para qualquer alteração que crie ou modifique páginas, partials, componentes, recipes, interações HTMX, Alpine.js, navegação, layout, estado visual, formulário, tabela, card, fluxo de autenticação ou teste frontend server-rendered.

O guia geral do projeto continua sendo fonte de referência, mas não substitui o contrato específico da issue. Confiar apenas no guia geral aumenta o risco de agentes esquecerem decisões importantes, como categoria responsiva, paths oficiais, partials, targets HTMX, estados de UI, testes obrigatórios, permissões, acessibilidade e segurança.

A regra é: nenhum agente deve iniciar implementação frontend sem antes preencher o contrato de handoff da issue ou PR.

#### Objetivo do handoff

O bloco de handoff transforma decisões arquiteturais em instruções operacionais para agentes de IA e revisores humanos.

Ele deve deixar explícito:

- o que será implementado;
- onde os arquivos devem ser criados;
- qual categoria responsiva da jornada;
- quais templates e partials serão usados;
- qual contrato HTMX será aplicado;
- quais estados de UI são obrigatórios;
- quais permissões devem ser respeitadas;
- quais dados vêm do domínio;
- quais componentes oficiais devem ser usados;
- quais requisitos de acessibilidade se aplicam;
- quais regras de segurança devem ser observadas;
- quais testes são obrigatórios;
- o que está fora de escopo.

O handoff não deve ser tratado como documentação burocrática. Ele é o contrato mínimo para permitir codificação autônoma sem reabrir arquitetura em cada PR.

#### Quando o bloco é obrigatório

O bloco de handoff é obrigatório para qualquer issue ou PR que envolva:

- nova página;
- nova jornada;
- nova worklist;
- novo formulário;
- novo modal;
- nova partial HTMX;
- nova action HTMX;
- novo componente Django include;
- alteração em componente oficial;
- alteração no shell;
- alteração na navegação;
- alteração em Tailwind tokens ou recipes;
- alteração em Alpine.js;
- alteração em estados de UI;
- alteração em fluxo de autenticação;
- alteração em testes frontend server-rendered.

Issues puramente backend, sem impacto visual ou contrato HTML/HTMX, não precisam preencher o bloco completo. Porém, se a issue alterar contexto, permissão, form, selector, policy ou service consumido por uma tela, deve ao menos declarar o impacto frontend esperado ou informar explicitamente que não há impacto.

#### Bloco padrão obrigatório

Toda issue/PR frontend deve conter o seguinte bloco:

```md
## Frontend Handoff Contract

### 1. Tipo de entrega
- [ ] Nova jornada
- [ ] Nova página
- [ ] Nova partial HTMX
- [ ] Novo formulário
- [ ] Nova worklist
- [ ] Novo modal
- [ ] Novo componente
- [ ] Alteração de componente existente
- [ ] Alteração de shell/navegação
- [ ] Alteração de design system/Tailwind
- [ ] Alteração de Alpine.js
- [ ] Alteração de testes
- [ ] Outro: <descrever>

### 2. Jornada e categoria responsiva
Jornada:
Categoria responsiva:
- [ ] mobile-primary
- [ ] desktop-optimized
- [ ] responsive-neutral
Justificativa da categoria:

### 3. Papel operacional e navegação
Papéis envolvidos:
- [ ] solicitante
- [ ] chefia
- [ ] almoxarifado
- [ ] admin
- [ ] outro: <descrever>
Item de navegação novo ou alterado?
- [ ] Não
- [ ] Sim
Se sim:
Label:
Grupo:
Route/URL:
Regra de active state:
Permissões/policies relacionadas:

### 4. Arquivos esperados
Templates:
- apps/web/templates/web/pages/<jornada>/...
Partials:
- apps/web/templates/web/pages/<jornada>/_...
Views:
- apps/web/views/...
Assets/Alpine, se aplicável:
- apps/web/static/web/...
Domínio:
- apps/<domain>/selectors.py
- apps/<domain>/services.py
- apps/<domain>/policies.py
- apps/<domain>/forms.py
- apps/<domain>/context.py
Testes:
- <paths esperados>

### 5. Dados e contrato de domínio
Selectors necessários:
Services necessários:
Policies necessárias:
Forms necessários:
Context builder/view model esperado:
Dados que NÃO devem ir para o HTML:

### 6. Templates e componentes
Componentes oficiais a usar:
- [ ] button.html
- [ ] badge.html
- [ ] alert.html
- [ ] form_field.html
- [ ] empty_state.html
- [ ] pagination.html
- [ ] modal_shell.html
- [ ] outro: <descrever>
Recipes aplicáveis:
- [ ] page layout
- [ ] worklist
- [ ] form page
- [ ] detail page
- [ ] modal
- [ ] table
- [ ] cards/list mobile
- [ ] empty state
- [ ] outro: <descrever>
Novos componentes propostos:
- [ ] Não
- [ ] Sim, justificar:

### 7. Contrato HTMX
Esta entrega usa HTMX?
- [ ] Não
- [ ] Sim
Se sim, declarar cada action:
Action:
Método:
URL/route:
Partial renderizado:
Target:
Swap:
Status de sucesso:
Headers HTMX:
Eventos emitidos:
Comportamento em 422:
Comportamento em 403:
Comportamento em 401/sessão expirada:
Comportamento em 409:
Loading state:
Feedback esperado:

### 8. Alpine.js
Esta entrega usa Alpine.js?
- [ ] Não
- [ ] Sim
Se sim:
Comportamento local controlado:
Estado mantido:
Onde será implementado:
Por que não é regra de negócio:
Eventos HTMX consumidos, se houver:

### 9. Estados de UI obrigatórios
- [ ] Loading
- [ ] Empty state
- [ ] Empty state por filtro
- [ ] Success
- [ ] Error
- [ ] Validation error
- [ ] Permission denied
- [ ] Session expired
- [ ] Conflict
- [ ] Disabled
- [ ] Outro: <descrever>
Como cada estado será renderizado:

### 10. Acessibilidade
Requisitos aplicáveis:
- [ ] Labels visíveis ou nomes acessíveis
- [ ] aria-invalid em campos inválidos
- [ ] aria-describedby para erros/help text
- [ ] aria-live para feedback dinâmico
- [ ] foco após submit HTMX
- [ ] foco após erro
- [ ] modal acessível
- [ ] navegação por teclado
- [ ] sem hover-only
- [ ] botões com type explícito
- [ ] ícones com nome acessível quando interativos
Comportamento de foco esperado:

### 11. Segurança frontend
- [ ] CSRF em requisições mutáveis
- [ ] Sem scripts inline soltos
- [ ] Sem handlers onclick/onchange/onload
- [ ] Sem |safe sem decisão explícita
- [ ] JSON via json_script quando necessário
- [ ] Sem dados sensíveis no DOM
- [ ] Redirects internos validados
- [ ] Permissão validada no backend
- [ ] Conteúdo de usuário renderizado como texto
Observações de segurança:

### 12. Testes obrigatórios
Django test client / HTML assertions:
- [ ] GET página 200
- [ ] template correto
- [ ] partial correta
- [ ] targets HTMX presentes
- [ ] hx-* attrs esperados
- [ ] estado vazio
- [ ] estado com dados
- [ ] permissões visuais
- [ ] endpoint protegido 403
- [ ] sessão expirada 401 com HX-Redirect/HX-Refresh
- [ ] validação 422
- [ ] conflito 409
- [ ] headers HTMX
- [ ] atributos de acessibilidade
Playwright necessário?
- [ ] Não
- [ ] Sim
Se sim, justificar:
Fluxo Playwright esperado:

### 13. Fora de escopo
Declarar explicitamente o que esta issue/PR não deve implementar:

### 14. Critérios de aceite
- [ ] Segue estrutura apps/web
- [ ] Não cria templates em apps/<domain>/templates/
- [ ] Não cria layout paralelo
- [ ] Não cria CSS paralelo
- [ ] Não altera tokens sem documentação
- [ ] Não cria componente genérico sem contrato
- [ ] Não coloca regra de negócio em template
- [ ] Não coloca autorização no frontend
- [ ] Testes mínimos passando
- [ ] Estados obrigatórios implementados
- [ ] Acessibilidade mínima validada
```

#### Regra de preenchimento

O bloco deve ser preenchido antes da implementação.

Não é aceitável deixar campos críticos em branco quando a entrega envolver a área correspondente.

Campos que não se aplicarem devem ser marcados explicitamente como:

```text
Não aplicável
```

Não é permitido remover seções do bloco para simplificar a issue. Se a entrega for pequena, as seções podem ser preenchidas de forma curta, mas devem permanecer visíveis.

#### Handoff para nova jornada

Para nova jornada, o handoff deve obrigatoriamente declarar:

- categoria responsiva;
- papel operacional;
- item de navegação, se houver;
- estrutura de templates;
- partials previstas;
- dados vindos do domínio;
- states obrigatórios;
- contrato HTMX;
- requisitos de acessibilidade;
- regras de segurança;
- testes mínimos;
- fora de escopo.

Nenhuma nova jornada deve ser implementada sem declarar se é:

- `mobile-primary`;
- `desktop-optimized`;
- `responsive-neutral`.

Essa categoria define layout, densidade visual, uso de tabela/cards, filtros, actions, responsividade e critérios de aceite.

#### Handoff para worklist

Para worklists, o handoff deve declarar:

- recipe de worklist aplicável;
- categoria responsiva;
- tabela desktop, se aplicável;
- cards/lista mobile, se aplicável;
- filtros;
- paginação;
- empty state real;
- empty state por filtro;
- actions por item;
- badges/status;
- target HTMX principal;
- partials de lista/tabela/cards;
- testes de estado vazio, estado com dados e permissão.

Não é permitido criar uma worklist sem seguir a recipe oficial.

#### Handoff para HTMX

Para qualquer action HTMX, o handoff deve declarar:

- método;
- URL/route;
- partial;
- target;
- swap;
- status de sucesso;
- headers;
- eventos;
- loading state;
- feedback;
- `422`;
- `403`;
- `401`;
- `409`;
- testes.

Não é permitido criar endpoint HTMX sem contrato explícito.

Não é permitido retornar HTML aleatório por endpoint.

Não é permitido usar `200` para todos os casos sem justificar status específicos.

#### Handoff para componente

Para novo componente ou alteração em componente oficial, o handoff deve declarar:

- propósito;
- quando usar;
- quando não usar;
- variantes permitidas;
- parâmetros mínimos;
- parâmetros proibidos;
- requisitos de acessibilidade;
- requisitos de segurança;
- exemplos de uso;
- testes esperados.

Não é permitido criar componente genérico com API ampla sem decisão documentada.

Se o padrão for grande, contextual ou instável, deve começar como recipe ou partial de jornada, não como include oficial.

#### Handoff para navegação

Para qualquer alteração de navegação, o handoff deve declarar:

- papel operacional;
- label orientado à tarefa;
- grupo;
- route/URL;
- active state;
- policy/permissão relacionada;
- teste de visibilidade;
- teste de acesso direto à rota protegida.

Itens de navegação devem ser alterados no context builder oficial de navegação. Não é permitido adicionar links de menu diretamente no shell ou em templates de jornada.

#### Handoff para segurança

Toda issue frontend deve confirmar que:

- não há scripts inline soltos;
- não há handlers nativos;
- não há uso de `|safe` sem decisão;
- não há JSON manual inseguro;
- não há dados sensíveis no DOM;
- CSRF está presente em actions mutáveis;
- permissão é validada no backend;
- redirects são internos e validados.

Se algum item de segurança precisar de exceção, a exceção deve ser registrada antes da implementação.

#### Handoff para testes

O handoff deve declarar os testes esperados antes do código.

Para toda alteração frontend server-rendered, o mínimo é:

- Django test client;
- assertions HTML;
- assertions de template/partial;
- assertions de permissões quando aplicável;
- assertions de acessibilidade mínima.

Playwright deve ser declarado quando a entrega envolver:

- fluxo crítico;
- modal com submit;
- HTMX + Alpine.js;
- múltiplos swaps;
- aprovação/rejeição;
- movimentação de estoque;
- operação destrutiva;
- gate de lançamento;
- regressão já identificada.

Se Playwright não for necessário, o handoff deve marcar explicitamente `Não` e justificar quando a entrega parecer interativa.

#### Revisão de PR

Todo PR frontend deve incluir o bloco de handoff preenchido na descrição ou referenciar a issue que contém o bloco preenchido.

O revisor deve verificar:

- se o código implementa o contrato declarado;
- se os arquivos foram criados nos caminhos corretos;
- se não houve criação de fundação paralela;
- se HTMX segue o contrato;
- se acessibilidade mínima foi implementada;
- se segurança frontend foi respeitada;
- se os testes cobrem o contrato;
- se o fora de escopo foi respeitado.

PRs que alterem frontend sem handoff preenchido devem ser considerados incompletos.

#### Padrões proibidos de handoff

Não é permitido:

- implementar frontend sem bloco de handoff;
- criar página sem categoria responsiva;
- criar partial HTMX sem target/swap/status;
- criar worklist sem recipe;
- criar componente sem contrato;
- alterar navegação fora do context builder;
- criar template em `apps/<domain>/templates/`;
- criar CSS paralelo;
- criar scripts inline soltos;
- implementar autorização no frontend;
- criar testes depois sem contrato prévio;
- remover seções do handoff por conveniência.

#### Critério para agentes de IA

Agentes de IA devem tratar o handoff como entrada obrigatória de implementação.

Antes de codar, o agente deve:

- ler o bloco de handoff;
- validar paths oficiais;
- identificar categoria responsiva;
- identificar components/recipes obrigatórios;
- identificar contrato HTMX;
- identificar states obrigatórios;
- identificar regras de segurança;
- identificar testes mínimos;
- confirmar fora de escopo.

Durante a implementação, o agente não deve tomar decisões arquiteturais silenciosas. Se o handoff estiver incompleto ou contradisser a documentação do projeto, o agente deve registrar a lacuna e propor ajuste antes de criar padrões novos.

O handoff é parte do processo de delivery e deve ser revisado junto com o código.

## 10. Worklists e detalhe

Worklists devem seguir uma recipe única por categoria responsiva, não um componente genérico `table.html` e não uma UI desenhada livremente por cada jornada.

Toda worklist deve seguir uma estrutura comum de página, com variações controladas conforme a categoria responsiva da jornada:

- `mobile-primary`;
- `desktop-optimized`;
- `responsive-neutral`.

A recipe de worklist deve garantir consistência entre jornadas como:

- Minhas solicitações;
- Aprovações pendentes;
- Fila de atendimento;
- Estoque;
- Movimentações;
- Materiais;
- Histórico.

O objetivo é evitar que cada jornada crie sua própria combinação de header, filtros, tabela, cards, ações, empty state, paginação, badges e feedback.

A estratégia adotada é recipe única de worklist, com variações por categoria responsiva.

Não será criado um componente genérico `table.html` neste momento. Tabelas completas têm muitas variações de coluna, action, estado, densidade, seleção, ordenação, responsividade, permissão e HTMX. Criar um include genérico agora tende a gerar API grande, frágil e difícil de manter.

Cada jornada também não deve desenhar sua lista livremente. Isso causaria inconsistência visual e funcional entre telas que deveriam se comportar como a mesma família de interface.

A worklist será uma recipe documentada, composta por partials específicas da jornada e componentes oficiais pequenos, como:

- `button.html`;
- `badge.html`;
- `alert.html`;
- `empty_state.html`;
- `pagination.html`;
- `form_field.html`.

### Recipe de worklist

Toda worklist deve seguir esta estrutura conceitual:

- page header;
- descrição curta da jornada;
- ações primárias;
- filtros;
- estado de loading, quando aplicável;
- conteúdo principal;
- empty state;
- paginação;
- feedback global/contextual.

Estrutura recomendada de templates:

```text
apps/web/templates/web/pages/<jornada>/
  list.html
  _filters.html
  _list.html
  _table.html
  _cards.html
  _empty_state.html
  _pagination.html
```

Nem toda jornada precisa ter todos esses arquivos. A estrutura deve ser aplicada conforme necessidade real. Porém, quando uma jornada tiver filtros, lista, tabela, cards, empty state ou paginação, os nomes e responsabilidades devem seguir essa convenção.

Responsabilidade dos arquivos:

- `list.html`: página completa; compõe shell da jornada, header, filtros e container principal;
- `_filters.html`: controles de filtro e busca da worklist;
- `_list.html`: fragmento principal atualizável por HTMX, quando aplicável; pode decidir entre renderizar `_table.html`, `_cards.html`, `_empty_state.html` e `_pagination.html`, mas não deve conter regra de negócio;
- `_table.html`: representação tabular para desktop ou telas maiores;
- `_cards.html`: representação em cards/lista para mobile quando a jornada for `mobile-primary`;
- `_empty_state.html`: estado vazio específico da jornada, preferencialmente usando `empty_state.html`;
- `_pagination.html`: paginação específica da jornada ou uso de `pagination.html`.

### Recipe para mobile-primary

Jornadas `mobile-primary` devem priorizar lista ou cards em mobile.

Exemplos:

- Minhas solicitações;
- Aprovações pendentes;
- Detalhes rápidos de solicitação;
- Histórico simples.

Em `mobile-primary`, o padrão deve ser:

- mobile: cards/lista simples;
- tablet/desktop: tabela simples ou lista expandida, conforme necessidade;
- ações principais visíveis;
- baixa densidade visual;
- campos prioritários;
- status evidente;
- filtros simples e colapsáveis quando necessário;
- paginação simples.

Cards mobile devem exibir apenas os dados essenciais para decisão ou acompanhamento.

Cada card deve conter, quando aplicável:

- identificador principal;
- status;
- título ou resumo;
- data relevante;
- responsável ou solicitante, quando útil;
- action principal;
- actions secundárias em menu ou área menos destacada.

Exemplo de campos prioritários para `Minhas solicitações`:

- número da solicitação;
- status;
- data de criação;
- resumo/primeiro item;
- última atualização;
- action de ver detalhe.

`mobile-primary` não deve tentar reproduzir todas as colunas da tabela desktop dentro do card. Dados secundários devem ir para a tela de detalhe.

### Recipe para desktop-optimized

Jornadas `desktop-optimized` devem priorizar tabela densa em desktop.

Exemplos:

- Fila de atendimento do Almoxarifado;
- Estoque;
- Movimentações;
- Materiais;
- Inventário.

Em `desktop-optimized`, o padrão deve ser:

- desktop: tabela densa;
- filtros visíveis ou em toolbar;
- uso eficiente de largura;
- status bem destacados;
- actions por linha claras;
- paginação completa;
- ordenação quando aplicável;
- seleção em massa apenas quando houver necessidade real;
- mobile: fallback funcional, não necessariamente equivalente em densidade.

Tabelas desktop devem priorizar comparação, triagem e operação rápida.

A tabela deve conter:

- cabeçalho claro;
- colunas alinhadas;
- status com badge oficial;
- actions por linha previsíveis;
- empty state consistente;
- paginação;
- estado de filtro sem resultados.

Não é obrigatório transformar toda tabela `desktop-optimized` em cards mobile completos. Para jornadas que não são `mobile-primary`, o mobile pode ser funcional, simplificado ou com scroll horizontal controlado, desde que não quebre o uso básico.

### Recipe para responsive-neutral

Jornadas `responsive-neutral` devem usar o padrão mais simples que atenda ao caso.

Exemplos:

- notificações;
- histórico simples;
- configurações secundárias;
- listas administrativas pequenas.

O padrão pode ser:

- tabela simples em desktop;
- lista simples em mobile;
- filtros mínimos;
- paginação quando necessário;
- empty state oficial.

### Header da worklist

Toda worklist deve ter header consistente.

O header deve conter:

- título da página;
- descrição curta, quando útil;
- action primária, quando existir;
- actions secundárias, quando existirem.

A action primária deve ser única por contexto sempre que possível.

Exemplos:

- Nova solicitação;
- Registrar movimentação;
- Cadastrar material.

Não deve haver múltiplos botões primários competindo visualmente na mesma área.

### Filtros

Filtros devem seguir a recipe da categoria responsiva.

Para `mobile-primary`:

- filtros mínimos;
- busca simples quando útil;
- filtros colapsáveis quando houver mais de dois controles;
- evitar toolbars densas;
- aplicar/limpar filtros de forma clara.

Para `desktop-optimized`:

- filtros visíveis;
- toolbar funcional;
- busca, status, período e responsáveis quando aplicável;
- densidade compatível com operação;
- preservar filtros na paginação.

Filtros HTMX devem declarar:

- target atualizado;
- swap esperado;
- estado de loading;
- comportamento de empty state filtrado;
- preservação de parâmetros.

Filtros não devem causar perda de contexto sem feedback.

### Empty state

Toda worklist deve ter empty state explícito.

Devem existir pelo menos dois tipos de empty state:

- vazio real;
- sem resultado para filtros.

O vazio real indica que ainda não existem registros relevantes.

O estado sem resultado para filtros indica que existem dados, mas nenhum corresponde aos filtros aplicados.

Esses estados não devem ser confundidos com erro de carregamento.

Empty state deve usar o componente oficial `empty_state.html` sempre que possível.

### Ações por item

Ações por item devem ser consistentes por categoria.

Regras obrigatórias:

- action principal visível;
- actions destrutivas com variant `danger`;
- actions destrutivas exigem confirmação quando aplicável;
- actions indisponíveis não devem aparecer se usuário não tem permissão;
- actions bloqueadas por estado podem aparecer `disabled` apenas se houver explicação útil;
- permissão deve ser validada no backend.

Ações em mobile devem evitar excesso de botões por card. Quando houver muitas actions, usar uma action principal e agrupar secundárias.

Ações em tabela desktop podem aparecer como botões compactos, links de action ou menu por linha, conforme recipe da jornada.

### Status e badges

Status em worklists devem usar o componente oficial `badge.html`.

Status iguais devem ter a mesma label e a mesma variante visual em todo o sistema.

O mapeamento entre status de domínio e variante visual deve ser feito antes do template, em context builder ou helper de apresentação.

Não é permitido que cada worklist defina cores próprias para status.

### HTMX em worklists

Worklists podem usar HTMX para:

- filtrar;
- paginar;
- ordenar;
- atualizar lista após action;
- abrir modal de detalhe/action;
- submeter action simples.

Toda interação HTMX da worklist deve seguir o contrato global HTMX:

- partial renderizado;
- target esperado;
- swap esperado;
- status HTTP esperado;
- headers HTMX utilizados;
- eventos emitidos, quando aplicável;
- comportamento em `422`;
- comportamento em `403`;
- comportamento em `409`.

O target principal de uma worklist deve ser estável e documentado.

Exemplo:

```html
<div id="requisitions-worklist"></div>
<div id="approvals-worklist"></div>
```

Targets baseados em hierarquia visual instável são proibidos.

### Tabela não será componente genérico agora

Não será criado um include genérico `table.html` no MVP inicial.

Motivos:

- tabelas têm colunas muito contextuais;
- actions variam por jornada;
- responsividade varia por categoria;
- seleção em massa pode ou não existir;
- ordenação pode ou não existir;
- permissões por linha variam;
- densidade varia entre `mobile-primary` e `desktop-optimized`;
- API genérica ficaria grande demais.

O padrão correto é documentar a recipe de tabela e implementar `_table.html` por jornada, reutilizando componentes pequenos como badge, button, pagination e empty_state.

Um componente de tabela só poderá ser considerado no futuro se múltiplas jornadas convergirem para uma API estável e pequena.

### Cards não serão componente genérico agora

Cards de worklist também não devem virar componente genérico inicialmente.

Motivos:

- conteúdo do card varia por jornada;
- hierarquia de dados varia por papel;
- actions variam por estado e permissão;
- `mobile-primary` exige decisões de produto específicas.

O padrão correto é documentar a recipe de card/lista e implementar `_cards.html` por jornada.

Componentes pequenos internos podem ser reutilizados, mas o card completo da jornada deve permanecer explícito até que surja repetição real.

### Acessibilidade de worklists

Worklists devem seguir o contrato obrigatório de acessibilidade.

Obrigatório:

- título claro;
- estrutura semântica;
- actions com nome acessível;
- status não dependente apenas de cor;
- foco visível;
- feedback após filtros HTMX;
- feedback após actions HTMX;
- empty state textual;
- paginação acessível;
- tabelas com cabeçalhos claros;
- cards mobile com labels compreensíveis;
- sem action dependente de hover.

Quando filtros atualizarem a lista via HTMX, a mudança deve ser comunicada por feedback textual ou região apropriada, especialmente quando o resultado ficar vazio.

### Testes mínimos de worklists

Toda worklist deve ter testes de contrato.

Testes obrigatórios para página completa:

- `GET` por usuário autorizado retorna `200`;
- template correto é usado;
- header da worklist existe;
- target principal da worklist existe;
- estado vazio real é renderizado;
- lista/tabela é renderizada quando há dados;
- actions aparecem conforme permissão;
- actions proibidas não aparecem para usuário sem permissão;
- badges de status usam labels esperadas;
- paginação aparece quando aplicável.

Testes obrigatórios para HTMX, quando aplicável:

- request HTMX de filtro retorna partial correta;
- request HTMX de paginação retorna partial correta;
- target esperado é compatível com a página;
- status HTTP correto é retornado;
- `403` é retornado para usuário sem permissão;
- `401` com `HX-Redirect` ou `HX-Refresh` é retornado para sessão expirada quando aplicável;
- `409` é retornado em conflito de domínio quando a action depender de estado;
- `422` é retornado em validação inválida quando houver formulário.

Para jornadas críticas, Playwright deve ser usado quando a worklist envolver:

- modal com submit;
- HTMX + Alpine.js;
- múltiplos swaps;
- aprovação/rejeição;
- movimentação de estoque;
- operação destrutiva;
- atualização parcial de tabela após action;
- gate de lançamento.

### Padrões proibidos de worklists

Não é permitido:

- cada jornada desenhar uma UI de lista completamente própria;
- criar componente genérico `table.html` agora;
- criar componente genérico `card.html` para worklists agora;
- usar cores locais para status;
- criar empty state diferente por improviso;
- usar tabela desktop sem estratégia mobile em jornada `mobile-primary`;
- replicar todas as colunas desktop dentro de card mobile;
- esconder action crítica em mobile;
- depender de hover para action por item;
- usar targets HTMX frágeis;
- misturar regra de negócio dentro de templates de tabela/card;
- passar model inteiro para componente visual quando context view model simples bastar.

Ao implementar uma nova worklist, agentes devem primeiro declarar a categoria responsiva da jornada:

- `mobile-primary`;
- `desktop-optimized`;
- `responsive-neutral`.

Depois devem seguir a recipe correspondente.

Agentes devem criar a worklist em `apps/web/templates/web/pages/<jornada>/`, usando conforme necessidade:

- `list.html`;
- `_filters.html`;
- `_list.html`;
- `_table.html`;
- `_cards.html`;
- `_empty_state.html`;
- `_pagination.html`.

Agentes devem reutilizar componentes oficiais pequenos e não criar componentes genéricos grandes.

Agentes não devem criar uma nova linguagem visual para a worklist. Qualquer variação visual recorrente deve ser proposta como ajuste de recipe ou design system.

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

O detalhe de solicitação é rota canônica única:

- route name: `web:requisition_detail`;
- path esperado: `/requisicoes/<id>/`;
- contexto opcional validado: `minhas`, `autorizacao`, `atendimento`.

Blocos comuns:

- cabeçalho;
- status;
- beneficiário/criador;
- itens;
- quantidades;
- histórico/eventos;
- observações;
- feedback/trace.

O action panel muda por contexto, papel, permissão e estado.

Regras:

- dados do action panel vêm de context builder;
- template não decide regra de autorização;
- contexto inválido deve gerar erro seguro ou fallback explícito;
- contexto não pode ampliar permissão;
- mesma requisição deve manter representação comum de status, itens e histórico em todos os contextos;
- actions indisponíveis por estado podem aparecer disabled apenas se isso ajudar a decisão operacional e com motivo claro;
- actions sem permissão não devem aparecer como caminho principal.

Não criar detalhes separados por jornada sem decisão arquitetural explícita. `Minhas solicitações`, `Aprovações` e `Atendimentos` devem apontar para a rota canônica quando exibirem a mesma requisição.

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

### Ações críticas

Ações críticas seguem padrão único de action panel, confirmação, submit e feedback.

Exemplos de ações críticas:

- autorizar;
- recusar;
- atender;
- cancelar requisição;
- descartar rascunho;
- movimentar estoque;
- qualquer action destrutiva, irreversível ou operacionalmente sensível.

Regras:

- action panel recebe actions já resolvidas do context builder;
- action destrutiva usa variant `danger`;
- confirmação é obrigatória para action destrutiva, irreversível ou de alto impacto operacional;
- `modal_shell.html` deve ser usado para confirmação rica ou form curto;
- submit HTMX retorna `200`, `204`, `403`, `409` ou `422` conforme contrato;
- sucesso atualiza painel, lista ou detalhe e emite feedback;
- conflito `409` mostra próxima action recomendada;
- backend valida permissão e estado sempre.

Não é permitido:

- usar confirmação browser `confirm()` como padrão;
- deixar action crítica depender apenas de hover;
- executar action crítica sem feedback;
- esconder regra de permissão no componente visual;
- confiar em action panel como autorização.

Cada action crítica deve ter teste de sucesso, permissão negada e erro/conflito esperado.

### Nova solicitação e edição de rascunho

Nova solicitação e edição de rascunho começam como uma jornada única server-rendered, com caminho evolutivo controlado.

MVP:

- mesma tela para criar e editar rascunho;
- submit convencional funciona sem JavaScript;
- HTMX pode melhorar lookup, validação e feedback;
- persistência por substituição completa;
- Django Form/FormSet ou estrutura equivalente no app de domínio;
- service valida domínio e salva;
- `422` re-renderiza form com erros;
- Alpine.js só mantém estado local pequeno.

Edição incremental item-a-item via HTMX não faz parte do MVP inicial. Essa evolução exige decisão posterior, motivada por dor real de uso ou necessidade operacional validada.

Regras:

- regra de domínio do rascunho permanece em service/policy do app de domínio;
- `apps/web` apenas orquestra tela, partials e resposta;
- lookup e validação local não substituem validação de domínio;
- erros de item devem apontar para campo/linha quando possível;
- erros globais devem explicar ação necessária sem expor detalhe interno.

### Formulários server-rendered

Forms HTML usam Django Forms como contrato principal de entrada.

Regras:

- forms vivem no app de domínio quando ligados a domínio;
- `apps/web` apenas instancia/orquestra;
- validação de campo fica no form;
- regra operacional fica no service/policy;
- form HTMX inválido retorna `422` com partial do form;
- submit convencional deve funcionar sem JavaScript;
- Alpine.js só pode melhorar estado local, não substituir validação;
- erros de domínio não associados a campo vão para erro global;
- todos os campos usam `form_field.html` quando aplicável.

Django Forms não substituem validação de domínio em services. Services continuam sendo a fonte de verdade para regras operacionais, concorrência, permissão contextual e transições.

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

## 11.4 Erros, suporte e trace ID

A UI deve exibir mensagens operacionais padronizadas com `trace_id` quando existir, sem expor stack trace ou detalhe interno.

Regras:

- nunca mostrar stack trace, exception class, SQL, payload interno ou policy interna;
- quando existir `trace_id`, exibir como "Código de suporte";
- erro `500` mostra mensagem genérica e `trace_id`;
- erro `403` explica falta de permissão sem revelar dados do recurso;
- erro `404` informa recurso indisponível/inexistente sem confirmar existência sensível;
- erro `409` explica conflito operacional e próxima action recomendada;
- erro `422` mostra erros de formulário por campo e erro global quando aplicável;
- fragments HTMX seguem o mesmo padrão de páginas completas;
- logs backend devem carregar o mesmo `trace_id`.

Componentes e regiões:

- `alert.html` para feedback;
- `global-errors` para erros críticos;
- partial específica quando erro pertence a uma jornada.

Mensagens devem ser seguras e acionáveis para usuário final. Detalhe técnico deve ficar em logs/server.

## 11.5 Estados de UI por jornada

Toda jornada deve declarar estados padrão antes da implementação:

- loading;
- empty;
- filtered-empty;
- error;
- forbidden;
- conflict;
- success feedback;
- disabled/unavailable action.

Regras:

- loading não remove contexto principal;
- empty real usa `empty_state.html`;
- erro de filtro sem resultado difere de lista vazia real;
- `403` mostra permissão negada sem vazar dados;
- `409` mostra conflito e próxima action recomendada;
- actions disabled devem explicar motivo quando útil;
- estados devem ter assertions HTML/HTMX nos testes.

Esses estados fazem parte do contrato da jornada. Agentes de IA não devem implementar página ou partial HTMX sem declarar e cobrir os estados relevantes para a jornada.

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
