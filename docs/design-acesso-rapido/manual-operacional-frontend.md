# Manual Operacional do Frontend Server-Rendered — Agentes de IA

Este manual é a fonte operacional para implementar o frontend server-rendered do piloto WMS-SAEP.

Use este arquivo para decidir onde criar arquivos, qual arquitetura seguir, quais contratos declarar, quais testes escrever e quais padrões são proibidos. Não use decisões locais quando este documento já define um padrão.

## 1. Regra de ouro para agentes

Agentes de IA não devem inventar arquitetura local. Antes de implementar, preencha o [Frontend Handoff Contract](#6-frontend-handoff-contract-obrigatório), confirme paths oficiais, declare contratos HTMX, acessibilidade, segurança e testes.

Use:

- Django templates server-rendered;
- `apps/web` para composição visual, shell, templates, partials, assets globais e views HTML;
- apps de domínio para `models`, `forms`, `selectors`, `services`, `policies`, validações e context builders;
- Tailwind CSS v4 CSS-first;
- HTMX com contrato global mínimo;
- Alpine.js apenas para estado local pequeno;
- design system híbrido token/recipe-first;
- includes oficiais pequenos e com contrato fino;
- navegação por papel operacional principal via context builder;
- responsividade por jornada;
- Django test client + assertions HTML/HTMX como mínimo.

Nunca faça:

- criar templates de página em `apps/<domain>/templates/`;
- criar CSS paralelo;
- editar `apps/web/static/web/dist/app.css` manualmente;
- criar shell paralelo;
- duplicar `base.html`;
- criar componente genérico sem contrato;
- criar `table.html` ou `card.html` genérico no MVP;
- colocar regra de negócio em template;
- executar query complexa em `apps/web`;
- decidir permissão no frontend;
- montar navegação no template;
- usar scripts inline soltos;
- usar handlers nativos como `onclick`, `onchange` ou `onload`;
- usar Tailwind CDN no app real;
- criar HTMX sem declarar partial, target, swap, status e testes;
- retornar login dentro de partial HTMX;
- usar `|safe` sem decisão explícita.

## 2. Como usar este documento

Antes de implementar:

1. Preencha o [Frontend Handoff Contract](#6-frontend-handoff-contract-obrigatório).
2. Identifique tipo de entrega.
3. Identifique categoria responsiva: `mobile-primary`, `desktop-optimized` ou `responsive-neutral`.
4. Identifique paths oficiais.
5. Identifique contrato HTMX, se houver.
6. Identifique components/recipes.
7. Declare requisitos de acessibilidade, foco e feedback.
8. Declare regras de segurança.
9. Escreva testes mínimos esperados.
10. Só então implemente.

Durante implementação:

- siga paths oficiais;
- mantenha regra de negócio no app de domínio;
- mantenha templates passivos;
- use componentes oficiais quando aplicável;
- registre lacunas em vez de criar exceções silenciosas.

Antes de concluir:

- rode checks relevantes;
- rode `git diff --check`;
- confirme critérios de aceite do handoff;
- confirme que fora de escopo foi respeitado.

## 3. Mapa rápido de decisões obrigatórias

| Tema | Decisão | Consequência prática para agente |
|---|---|---|
| Estrutura física | UI em `apps/web` | Templates em `apps/web/templates/web/pages/<jornada>/` |
| Domínio | Apps de domínio decidem regra | Services, selectors, policies, forms e context builders ficam no domínio |
| Views HTML | Views finas em `apps/web/views/` | View orquestra renderização; não contém regra de negócio |
| Tailwind | v4 CSS-first | Edite `styles.css`; nunca edite `dist/app.css` manualmente |
| HTMX | Contrato global mínimo | Toda action declara partial, target, swap, status, headers, eventos e testes |
| Alpine.js | Estado local pequeno | Não usar para permissão, validação de domínio ou workflow |
| Design system | Token/recipe-first | Comece por recipe; promova para include só com contrato fino |
| Includes | Pequenos e semânticos | Componentes recebem dados simples, não `user`, `request`, `model`, `object`, `queryset` ou `policy` |
| Navegação | Allowlist por papel | Alterar apenas context builder de navegação |
| Responsividade | Por jornada | Declare categoria antes de desenhar layout |
| Worklists | Recipe por categoria | Não criar `table.html` genérico nem UI livre por jornada |
| Auth | Login/logout HTML em `apps/web` | Não consumir API DRF auth via HTMX como padrão |
| Acessibilidade | Contrato obrigatório | Declare foco, `aria-live`, labels, erros e testes |
| Segurança | Secure defaults | Sem inline script, sem `|safe`, CSRF obrigatório, redirects internos validados |
| Testes | Django client + HTML/HTMX | Playwright só em fluxo crítico ou gate |
| Delivery | PR1 fundação, PR2 primeira jornada | Não iniciar jornada antes da fundação mínima |

## 4. Estrutura oficial de arquivos

Crie frontend server-rendered apenas nos caminhos oficiais.

```text
apps/web/
  urls.py
  htmx.py
  navigation.py
  views/
    auth.py
    requisitions.py
    ...
  templates/web/
    layouts/
      base.html
      app_shell.html
      auth_shell.html
    components/
      button.html
      badge.html
      alert.html
      form_field.html
      empty_state.html
      pagination.html
      modal_shell.html
    pages/
      <jornada>/
        list.html
        detail.html
        form.html
        _filters.html
        _list.html
        _table.html
        _cards.html
        _empty_state.html
        _pagination.html
  static/web/
    src/styles.css
    dist/app.css
    js/

apps/<domain>/
  models.py
  forms.py
  selectors.py
  services.py
  policies.py
  context.py
  tests/
```

Regras:

- `apps/web` renderiza HTML.
- Apps de domínio decidem regra.
- Templates de página ficam em `apps/web/templates/web/pages/<jornada>/`.
- Partials HTMX ficam junto da jornada.
- Componentes compartilhados ficam em `apps/web/templates/web/components/`.
- Layouts ficam em `apps/web/templates/web/layouts/`.
- Assets globais ficam em `apps/web/static/web/`.
- Views HTML ficam em `apps/web/views/`.
- Rotas HTML ficam em `apps/web/urls.py` com `app_name = "web"`.

### 4.1 Matriz: onde colocar cada coisa

| Item | Caminho correto | Proibido |
|---|---|---|
| Página HTML completa | `apps/web/templates/web/pages/<jornada>/` | `apps/<domain>/templates/` |
| Partial HTMX | `apps/web/templates/web/pages/<jornada>/_*.html` | partial solta sem jornada ou em app de domínio |
| Layout/shell | `apps/web/templates/web/layouts/` | shell paralelo por jornada |
| Componente visual | `apps/web/templates/web/components/` | componente com `model`, `user`, `request`, `queryset` ou `policy` |
| View HTML | `apps/web/views/` | regra de negócio dentro da view |
| URL HTML | `apps/web/urls.py` | hardcode de path quando há rota nomeada |
| Navegação | `apps/web/navigation.py` ou `apps/web/context/navigation.py` | links diretamente no shell com `if` de permissão |
| Helper HTMX | `apps/web/htmx.py` | headers HTMX escritos manualmente em toda view |
| Selector | `apps/<domain>/selectors.py` | query complexa em `apps/web` |
| Service | `apps/<domain>/services.py` | mutação de domínio em template/view |
| Policy | `apps/<domain>/policies.py` | `if` de permissão no template |
| Form | `apps/<domain>/forms.py` | validação de domínio em Alpine.js |
| Context builder/presenter | `apps/<domain>/context.py` ou módulo equivalente | template calculando label/status/permissão |
| Tailwind tokens/recipes | `apps/web/static/web/src/styles.css` | CSS paralelo ou editar `dist/app.css` |
| JS controlado | `apps/web/static/web/js/` | script inline solto em template |

## 5. Context builders e camada de apresentação

Use camada híbrida:

- domínio prepara dados simples de UI;
- `apps/web` compõe templates e partials;
- templates renderizam, não decidem regra.

Apps de domínio devem expor selectors, services, policies, forms e context builders/presenters para:

- labels;
- `status_variant`;
- booleans de ação, como `can_cancel`, `can_authorize`;
- URLs de actions;
- textos de empty state;
- listas paginadas já filtradas e autorizadas;
- mensagens seguras de domínio;
- metadados mínimos para templates e partials.

`apps/web` não deve:

- calcular status visual;
- decidir permissão;
- executar queryset complexa;
- aplicar regra operacional;
- decidir workflow.

Templates e includes recebem dados simples. Não recebem `request`, `user`, `model`, `object`, `queryset`, `policy` ou permissão bruta para decidir comportamento.

### 5.1 URLs HTML oficiais

Rotas HTML server-rendered vivem em `apps/web/urls.py` com `app_name = "web"`.

Use nomes estáveis:

- `web:login`;
- `web:logout`;
- `web:home`;
- `web:requisitions_mine`;
- `web:requisition_create`;
- `web:requisition_detail`;
- `web:authorizations_list`;
- `web:fulfillments_list`.

Partials e actions HTMX seguem padrão:

```text
web:<jornada>_<acao>
```

Use `reverse()` ou `{% url %}`. Não hardcode path quando houver rota nomeada.

### 5.2 Superfícies backend habilitadoras

Antes das telas operacionais, confirme que as superfícies necessárias existem no backend ou estão previstas no handoff.

Auth/sessão:

- `GET /api/v1/auth/csrf/`;
- `POST /api/v1/auth/login/`;
- `POST /api/v1/auth/logout/`;
- `GET /api/v1/auth/me/`.

Regras:

- o login HTML usa views server-rendered em `apps/web`;
- APIs de auth podem continuar para contratos externos/futuros;
- templates não devem depender de fetch client-side para descobrir papel/permissões.

Lookup de beneficiário:

- `GET /api/v1/users/beneficiary-lookup/?q=...`;
- mínimo de 3 caracteres;
- retorno curto;
- sem paginação;
- só usuários ativos e aptos ao fluxo.

Leituras de requisição:

- `GET /api/v1/requisitions/`: visibilidade operacional ampla;
- `GET /api/v1/requisitions/mine/`: `Minhas solicitações`;
- `GET /api/v1/requisitions/{id}/`: detalhe canônico.

Rascunho:

- update explícito por substituição completa.

APIs DRF são preservadas quando forem contrato útil para backend/frontend, integrações ou superfícies futuras. O frontend HTML não deve consumir API JSON automaticamente quando houver contrato server-rendered mais adequado.

### 5.3 Seed mínima e operação local

Deve existir comando oficial para cenário mínimo do piloto:

```text
seed_pilot_minimo
rtk make seed-pilot-minimo
```

Fluxo local esperado:

```text
rtk make setup
rtk make seed-pilot-minimo
```

Seed mínima deve cobrir:

- usuários operacionais principais;
- 1 usuário inativo apenas para autenticação;
- setores coerentes;
- material ativo com saldo confortável;
- material ativo com saldo baixo;
- material ativo sem estoque associado;
- material inativo;
- requisição rascunho;
- requisição aguardando autorização;
- requisição autorizada com autorização parcial;
- requisição atendida parcialmente;
- ao menos uma requisição criada para terceiro.

## 6. Frontend Handoff Contract obrigatório

Toda issue ou PR de frontend deve conter o bloco abaixo preenchido antes da implementação.

Obrigatório para:

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

Issues puramente backend não precisam do bloco completo. Se alterarem contexto, permissão, form, selector, policy ou service consumido por tela, devem declarar impacto frontend ou dizer `Não há impacto frontend`.

Não remova seções do bloco. Quando algo não se aplicar, escreva `Não aplicável`.

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
Foco após sucesso:
Foco após erro:
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
Tipo de interação:
- [ ] Página completa
- [ ] Partial HTMX
- [ ] Formulário
- [ ] Modal
- [ ] Worklist
- [ ] Tabela
- [ ] Card mobile
- [ ] Navegação
- [ ] Componente novo

Requisitos aplicáveis:
- [ ] Heading/landmark correto
- [ ] Labels visíveis ou nomes acessíveis
- [ ] aria-invalid em campos inválidos
- [ ] aria-describedby para erros/help text
- [ ] aria-live para feedback dinâmico
- [ ] foco após sucesso HTMX
- [ ] foco após erro HTMX
- [ ] foco inicial em modal
- [ ] retorno de foco ao fechar modal
- [ ] navegação por teclado
- [ ] sem hover-only
- [ ] botões com type explícito
- [ ] ícones interativos com nome acessível

Região aria-live usada:

Comportamento de foco após sucesso:

Comportamento de foco após erro:

Comportamento de foco em modal, se aplicável:

Como será testado:

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

Regras:

- Todo PR frontend deve incluir este bloco preenchido na descrição ou referenciar issue que contém o bloco preenchido.
- PR sem handoff preenchido é incompleto.
- Revisor deve comparar código com contrato declarado.
- Agente deve registrar lacuna se o handoff estiver incompleto ou contradizer este manual.

## 7. Contrato de acessibilidade para agentes

### 7.1 Política geral

WCAG AA é objetivo geral. O mecanismo real é contrato obrigatório por tipo de entrega. Acessibilidade não é checklist final.

Declare acessibilidade no handoff e implemente durante a entrega.

Nunca faça:

- ação dependente apenas de hover;
- ícone interativo sem nome acessível;
- erro indicado apenas por cor;
- campo inválido sem `aria-invalid`;
- erro de campo sem associação semântica;
- modal sem controle de foco;
- action HTMX que altera conteúdo sem feedback;
- `div` clicável sem semântica e teclado.

### 7.2 Matriz tipo de entrega -> requisitos obrigatórios

| Tipo | Requisitos obrigatórios |
|---|---|
| Página completa | `<main id="main-content">`, heading principal, ordem lógica de headings, foco visível, navegação por teclado |
| Partial HTMX | target declarado, foco pós-swap declarado, feedback declarado, não renderizar página completa indevida |
| Formulário | label visível ou nome acessível, erro associado, `aria-invalid`, `aria-describedby`, foco no primeiro erro ou resumo, botão submit com `type` explícito |
| Action HTMX | feedback em `aria-live`, foco após sucesso, foco após erro, loading state, `422`, `403`, `401`, `409` conforme contrato |
| Modal | `role="dialog"`, `aria-modal`, nome acessível, foco inicial, retorno de foco, Escape quando permitido |
| Worklist | título claro, status textual, filtros acessíveis, empty state textual, paginação acessível |
| Tabela | headers claros, actions com nome acessível, status não dependente só de cor, caption ou descrição quando útil |
| Card mobile | labels compreensíveis, status textual, action principal clara, não replicar todas as colunas desktop |
| Navegação | `<nav aria-label="Navegação principal">`, item ativo claro, drawer mobile acessível, teclado, sem hover-only |
| Componente novo | nome acessível, estados, variantes, requisitos de teclado, testes |

### 7.3 Foco e feedback em HTMX

| Caso | Regra de foco e feedback |
|---|---|
| Sucesso com fragmento | Declarar região atualizada; foco no heading, alert ou item atualizado conforme contexto |
| Sucesso com modal fechado | Foco retorna ao disparador ou item atualizado |
| Validação `422` | Foco vai para resumo de erros ou primeiro campo inválido |
| Permissão `403` | Foco vai para `#global-errors` ou alert contextual |
| Conflito `409` | Foco vai para painel/alert de conflito |
| Sessão `401` | Usar `HX-Redirect` ou `HX-Refresh`; nunca injetar login em partial |
| Filtro de worklist | Foco permanece no filtro ou vai para resumo de resultados; mudança deve ser anunciada |
| Paginação HTMX | Foco vai para início da lista atualizada ou heading da worklist |

### 7.4 Landmarks e headings

Use:

- skip link para `#main-content`;
- `<main id="main-content">` no shell;
- `<nav aria-label="Navegação principal">` na navegação principal;
- um único `h1` por página completa;
- headings em ordem lógica.

Não use:

- partial com `h1` salvo quando substituir o conteúdo principal;
- heading só para efeito visual;
- navegação sem nome acessível;
- drawer mobile sem foco controlado.

### 7.5 Testes mínimos de acessibilidade

Assertions mínimas quando aplicável:

- existe `aria-live`;
- existe `aria-invalid="true"` em campo inválido;
- `aria-describedby` aponta para erro/help text;
- campo tem `<label>` ou nome acessível;
- botão submit tem `type="submit"`;
- modal tem `role="dialog"` e `aria-modal`;
- botões têm nome acessível;
- erro não é só texto solto sem associação semântica;
- navegação usa `aria-label`;
- item ativo é identificável.

Não basta testar texto de erro. Teste associação semântica entre campo e erro.

## 8. Contrato HTMX

HTMX é progressive enhancement para interações server-rendered. Endpoints HTMX não retornam HTML arbitrário.

Toda action HTMX deve declarar:

- action;
- método;
- URL/route;
- partial;
- target;
- swap;
- status de sucesso;
- headers;
- eventos;
- loading state;
- foco;
- feedback;
- comportamento em `422`;
- comportamento em `403`;
- comportamento em `401`;
- comportamento em `409`;
- testes.

Páginas completas e partials ficam na mesma jornada:

```text
apps/web/templates/web/pages/<jornada>/<page>.html
apps/web/templates/web/pages/<jornada>/_<partial>.html
```

### 8.1 Status HTTP

| Status | Uso |
|---|---|
| `200 OK` | Operação bem-sucedida com fragmento HTML para swap |
| `204 No Content` | Operação bem-sucedida sem fragmento; emitir evento HTMX quando houver efeito na UI |
| `400 Bad Request` | Request inválido ou parâmetros malformados |
| `401 Unauthorized` | Usuário não autenticado/sessão expirada; usar `HX-Redirect` ou `HX-Refresh`; nunca renderizar login dentro de partial |
| `403 Forbidden` | Usuário autenticado sem permissão; feedback seguro sem vazar dados |
| `404 Not Found` | Recurso inexistente/indisponível; feedback contextual ou global |
| `409 Conflict` | Conflito de domínio ou estado concorrente; mostrar próxima ação recomendada |
| `422 Unprocessable Entity` | Form inválido; renderizar partial do form com erros por campo e erro global |
| `500 Internal Server Error` | Erro inesperado; feedback genérico e `trace_id` quando existir |

### 8.2 Targets e swaps

Use IDs estáveis:

```html
<div id="global-feedback" aria-live="polite" aria-atomic="true"></div>
<div id="global-errors" aria-live="assertive" aria-atomic="true"></div>
<div id="modal-root"></div>
<div id="requisitions-worklist"></div>
<div id="requisition-form"></div>
```

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

Não use:

- target baseado em `nth-child`;
- target baseado em hierarquia visual profunda;
- login HTML como fragment operacional;
- `200` para todos os erros;
- header manual repetido sem helper.

### 8.3 Helpers HTMX oficiais

Helpers devem viver em `apps/web/htmx.py`:

- `render_htmx(request, template, context, *, status=200)`;
- `htmx_redirect(url, *, status=401|200)`;
- `htmx_refresh(*, status=401|200)`;
- `htmx_trigger(response, event, payload=None, after="receive|swap|settle")`;
- `htmx_retarget(response, target)`;
- `htmx_validation_error(request, template, context)`;
- `htmx_forbidden(request, template, context)`;
- `htmx_conflict(request, template, context)`;
- `htmx_session_expired(login_url)`.

Views não devem escrever headers HTMX manualmente sem justificativa. Se uma action exigir header não coberto, adicione helper pequeno e genérico ou registre exceção.

## 9. Tailwind CSS e direção visual

### 9.1 Tailwind CSS v4 CSS-first

Arquivo oficial de entrada:

```text
apps/web/static/web/src/styles.css
```

Arquivo oficial compilado:

```text
apps/web/static/web/dist/app.css
```

`styles.css` deve conter:

```css
@import "tailwindcss";
```

Use:

- `@source` para templates Django autorizados;
- `@theme` para tokens visuais;
- `@layer components` e `@apply` apenas para recipes estáveis, repetidas e documentadas.

Scripts oficiais:

```json
{
  "scripts": {
    "css:dev": "tailwindcss -i apps/web/static/web/src/styles.css -o apps/web/static/web/dist/app.css --watch",
    "css:build": "tailwindcss -i apps/web/static/web/src/styles.css -o apps/web/static/web/dist/app.css --minify"
  }
}
```

Template base carrega só CSS compilado:

```django
{% load static %}
<link rel="stylesheet" href="{% static 'web/dist/app.css' %}">
```

Não use:

- Tailwind CDN no app real;
- `tailwind.config.js` por hábito;
- classes dinâmicas como `class="bg-{{ color }}-600"`;
- CSS paralelo por jornada;
- edição manual de `dist/app.css`;
- variações visuais sem atualizar design system.

### 9.2 Tokens obrigatórios

Tokens iniciais:

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

Semântica:

| Token | Uso |
|---|---|
| `success` | concluído, aprovado, disponível |
| `warning` | pendente, atenção, aguardando ação |
| `danger` | erro, rejeitado, bloqueado, ação destrutiva |
| `info` | informação, status neutro, orientação |
| `brand` | ação primária e navegação ativa |

Não crie novas cores de status por página.

### 9.3 Direção visual

Direção oficial:

- institucional sóbria como base global;
- operacional densa nas jornadas `desktop-optimized`;
- mobile limpo e direto nas jornadas `mobile-primary`;
- sem estética SaaS genérica, promocional ou excessivamente expressiva.

| Categoria | Densidade | Lista/tabela | Filtros | Ações |
|---|---|---|---|---|
| `mobile-primary` | baixa | cards/lista no mobile; tabela simples opcional no desktop | simples, colapsáveis se necessário | ação principal evidente |
| `desktop-optimized` | alta controlada | tabela densa no desktop; mobile funcional/fallback | ricos, toolbar funcional | ações por linha claras |
| `responsive-neutral` | média/baixa | padrão simples | mínimos | institucionais |

Use:

- fundo claro;
- superfícies brancas/neutras;
- bordas discretas;
- sombras leves ou inexistentes;
- raios moderados;
- cor primária com parcimônia;
- status com cor + texto;
- tipografia funcional.

Não use:

- gradientes decorativos;
- sombras fortes em cards comuns;
- cards decorativos para substituir tabelas operacionais;
- múltiplos botões primários concorrentes;
- animação ornamental;
- ícone decorativo sem função;
- densidade desktop em jornada `mobile-primary`.

## 10. Design system e includes oficiais

O design system é híbrido, token/recipe-first.

Use recipes para:

- layouts;
- grids;
- dashboards;
- tabelas completas;
- toolbars;
- estruturas complexas de formulário;
- worklists.

Promova para include apenas quando o padrão:

- aparece em três ou mais telas;
- tem semântica clara;
- tem variações limitadas;
- exige acessibilidade consistente;
- tem estados padronizados;
- não depende fortemente do contexto da página;
- pode ter API simples;
- reduz manutenção centralizada.

Includes oficiais iniciais:

- `button.html`;
- `badge.html`;
- `alert.html`;
- `form_field.html`;
- `empty_state.html`;
- `pagination.html`;
- `modal_shell.html`.

Todos ficam em:

```text
apps/web/templates/web/components/
```

### 10.1 Regras para todos os includes

Todo include deve declarar:

- propósito;
- quando usar;
- quando não usar;
- variantes permitidas;
- parâmetros mínimos;
- parâmetros proibidos;
- requisitos de acessibilidade;
- requisitos de segurança;
- exemplo canônico;
- critérios de teste.

Parâmetros permitidos por padrão, quando fizerem sentido:

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

Parâmetros HTMX permitidos apenas em componentes de ação, quando documentados:

- `hx_get`;
- `hx_post`;
- `hx_target`;
- `hx_swap`;
- `hx_confirm`;
- `hx_trigger`.

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

Evite `extra_classes`. Se necessário, documente como exceção controlada.

### 10.2 `button.html`

| Campo | Regra |
|---|---|
| Propósito | Renderizar ações clicáveis consistentes e acessíveis |
| Usar para | ação primária/secundária/destrutiva, link com aparência de botão, submit, botão HTMX simples |
| Não usar para | links comuns em texto, ícone isolado sem nome, menu composto, autorização |
| Variantes | `primary`, `secondary`, `outline`, `ghost`, `danger` |
| Tamanhos | `sm`, `md`, `lg` |
| Tipos | `button`, `submit`, `reset` |
| A11y | nome acessível, `type` explícito, disabled semântico, loading evita duplo submit |

Exemplo:

```django
{% include "web/components/button.html" with label="Salvar" variant="primary" type="submit" %}
```

Proibido:

```django
{% include "web/components/button.html" with user=request.user permission="requisitions.cancel" object=requisition %}
```

### 10.3 `badge.html`

| Campo | Regra |
|---|---|
| Propósito | Renderizar status, estados e classificações curtas |
| Usar para | status de requisição, estoque, aprovação, alerta |
| Não usar para | texto longo, erro completo, botão, link principal, permissão |
| Variantes | `neutral`, `info`, `success`, `warning`, `danger` |
| A11y | status textual; não depender só de cor |

Mapeamento entre status de domínio e variante visual deve ocorrer no context builder/presenter, não no include.

### 10.4 `alert.html`

| Campo | Regra |
|---|---|
| Propósito | Feedback textual acessível |
| Usar para | sucesso, erro global, aviso, informação, permissão negada, conflito |
| Variantes | `info`, `success`, `warning`, `danger` |
| Segurança | não expor stack trace, SQL, exception class ou detalhe interno |
| A11y | compatível com `aria-live` quando dinâmico |

### 10.5 `form_field.html`

| Campo | Regra |
|---|---|
| Propósito | Campo com label, help text, erro e acessibilidade |
| Usar para | inputs Django forms, selects, textareas, campos com erro |
| Não usar para | layout completo de formulário, fieldset complexo, múltiplos inputs sem contrato |
| A11y | label, erro associado, `aria-invalid`, `aria-describedby` |

Pode receber `field` de Django Form quando isso simplificar renderização sem esconder regra de negócio.

### 10.6 `empty_state.html`

| Campo | Regra |
|---|---|
| Propósito | Estado vazio consistente |
| Usar para | lista vazia, filtro sem resultado, fila vazia, tabela sem itens |
| Variantes | `default`, `filtered`, `permission` |
| Regras | não esconder erro como vazio; diferenciar vazio real de filtro sem resultado |

### 10.7 `pagination.html`

| Campo | Regra |
|---|---|
| Propósito | Navegação de páginas acessível |
| Usar para | listas/tabelas paginadas, resultados filtrados |
| Regras | estado atual, anterior/próximo claros, preservar filtros, HTMX quando parcial |
| A11y | sem depender apenas de ícones |

### 10.8 `modal_shell.html`

| Campo | Regra |
|---|---|
| Propósito | Estrutura acessível para modais |
| Usar para | confirmação, form curto, conflito, detalhe rápido |
| Não usar para | fluxo longo, form complexo, processo multi-etapa, conteúdo que deveria ser página |
| A11y | `role="dialog"`, `aria-modal`, nome acessível, foco inicial, retorno de foco, Escape quando permitido |

Alpine.js pode controlar abertura, fechamento e foco. Não pode conter regra de negócio, autorização ou validação de domínio.

### 10.9 Componentes proibidos no MVP

Não crie:

- `action.html`;
- `widget.html`;
- `panel.html`;
- `block.html`;
- `layout.html`;
- `table.html` genérico;
- `card.html` genérico.

Use recipe ou partial específica de jornada.

## 11. Navegação por papel

A navegação principal usa allowlist por papel operacional principal, montada no backend por context builder. Template só renderiza.

Módulo recomendado:

```text
apps/web/navigation.py
```

ou:

```text
apps/web/context/navigation.py
```

Funções esperadas:

- `build_navigation_for_user(user)`;
- `get_navigation_context(request)`.

Estrutura conceitual:

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
        ],
    },
]
```

Template:

```django
{% for group in navigation %}
  {% for item in group.items %}
    ...
  {% endfor %}
{% endfor %}
```

Não use condicionais de permissão no template para montar menu.

### 11.1 Papéis e itens esperados

| Papel | Itens esperados |
|---|---|
| Solicitante | Nova solicitação, Minhas solicitações |
| Chefia | Aprovações pendentes, Histórico de aprovações |
| Almoxarifado | Fila de atendimento, Estoque, Movimentações, Materiais |
| Admin | Usuários, Permissões, Configurações |

Nomes finais podem seguir domínio real, mas labels devem ser orientados a tarefas. Não use labels técnicos como `Requisitions`, `Stock`, `Users app`, `Materials module`.

### 11.2 Regras

Use:

- uma árvore de navegação para desktop e mobile;
- sidebar desktop;
- drawer/menu mobile;
- labels textuais;
- item ativo resolvido no backend;
- URLs resolvidas por `reverse()` ou `{% url %}`.

Não use:

- menu como autorização;
- árvore separada para mobile;
- item local criado direto em template;
- query pesada para contador sem decisão explícita;
- `request.user` passado para include decidir autorização.

Toda view/action continua validando autenticação e permissão no backend.

### 11.3 Testes de navegação

Teste:

- solicitante vê apenas itens esperados;
- chefia vê itens esperados;
- almoxarifado vê itens esperados;
- admin vê itens esperados;
- usuário sem permissão não vê item restrito;
- item ativo é marcado;
- sidebar e drawer usam mesma estrutura;
- rota protegida continua bloqueada quando acessada diretamente.

## 12. Worklists, tabelas e cards

Worklists seguem recipe única por categoria responsiva. Não crie componente genérico `table.html` nem `card.html` no MVP.

Estrutura:

- page header;
- ações principais;
- filtros;
- conteúdo principal;
- tabela desktop quando aplicável;
- cards/lista mobile quando `mobile-primary`;
- empty state;
- pagination;
- feedback HTMX.

Templates recomendados:

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

| Categoria | Regra |
|---|---|
| `mobile-primary` | mobile usa cards/lista; desktop pode usar tabela simples; baixa densidade; ação principal evidente |
| `desktop-optimized` | desktop usa tabela densa; filtros ricos; ações por linha; mobile funcional/fallback |
| `responsive-neutral` | padrão simples; tabela/lista conforme necessidade |

### 12.1 Header

Toda worklist tem:

- título;
- descrição curta quando útil;
- ação primária única quando existir;
- ações secundárias quando existirem.

Não use múltiplos botões primários concorrentes.

### 12.2 Filtros

`mobile-primary`:

- filtros mínimos;
- busca simples;
- filtros colapsáveis se houver mais de dois controles.

`desktop-optimized`:

- filtros visíveis;
- toolbar funcional;
- busca, status, período e responsáveis quando aplicável;
- filtros preservados na paginação.

Filtros HTMX declaram:

- target;
- swap;
- loading;
- empty state filtrado;
- preservação de parâmetros;
- foco/feedback.

### 12.3 Empty state

Declare dois estados:

- vazio real;
- sem resultado para filtros.

Use `empty_state.html` quando possível. Não confunda erro de carregamento com estado vazio.

### 12.4 Ações por item

Use:

- ação principal visível;
- `danger` para destrutiva;
- confirmação para destrutiva/irreversível;
- ações indisponíveis ausentes quando falta permissão;
- `disabled` com motivo quando bloqueio por estado ajuda usuário;
- validação backend sempre.

Mobile evita excesso de botões por card. Desktop pode usar botões compactos, links de ação ou menu por linha.

### 12.5 Status

Use `badge.html`. Status igual tem mesma label e mesma variante em todo sistema. Mapeamento status -> variante ocorre antes do template.

### 12.6 HTMX em worklists

Pode usar HTMX para:

- filtrar;
- paginar;
- ordenar;
- atualizar lista após action;
- abrir modal de action/detalhe;
- submeter action simples.

Target principal deve ser estável:

```html
<div id="requisitions-worklist"></div>
<div id="approvals-worklist"></div>
```

### 12.7 Testes de worklist

Teste:

- `GET` autorizado retorna `200`;
- template correto;
- header existe;
- target principal existe;
- vazio real;
- estado com dados;
- ações por permissão;
- status badges esperados;
- paginação quando aplicável;
- HTMX filtro/paginação retorna partial correta;
- `401`, `403`, `409`, `422` quando aplicável;
- atributos de acessibilidade.

## 13. Auth HTML

Login/logout HTML vivem em `apps/web`, usam sessão Django, Django Forms, templates server-rendered, CSRF e componentes oficiais.

Views:

```text
apps/web/views/auth.py
```

Templates:

```text
apps/web/templates/web/pages/auth/
  login.html
  logged_out.html
  password_reset_request.html
  password_reset_done.html
  password_reset_confirm.html
  password_reset_complete.html
```

Shell público, se necessário:

```text
apps/web/templates/web/layouts/auth_shell.html
```

Regras:

- login funciona sem JavaScript;
- HTMX pode melhorar erro/feedback, mas não é obrigatório;
- não consumir endpoint DRF auth via HTMX como padrão;
- reaproveitamento deve ocorrer em services/policies/validações, não misturando contrato JSON com HTML;
- logout deve preferir `POST` com CSRF;
- `next` deve ser interno e validado;
- mensagens de erro são genéricas, como `Credenciais inválidas.`;
- não revelar usuário inexistente, senha incorreta, usuário inativo ou permissão insuficiente.

Testes de login:

- `GET` login retorna `200`;
- template correto;
- formulário contém CSRF;
- labels existem;
- botão submit tem `type`;
- credenciais inválidas retornam erro acessível;
- credenciais válidas criam sessão;
- redirect interno esperado;
- `next` interno válido respeitado;
- `next` externo rejeitado/ignorado;
- usuário autenticado acessando login é redirecionado conforme política.

Testes de logout:

- encerra sessão;
- exige método definido;
- `POST` usa CSRF;
- redireciona para rota pública;
- usuário não autenticado tem comportamento seguro.

Se login usar HTMX:

- `POST` HTMX inválido retorna partial/form com erro acessível;
- não retorna JSON;
- não injeta shell completo dentro de partial.

## 14. Formulários, detalhe e ações críticas

### 14.1 Formulários server-rendered

Use Django Forms como contrato principal de entrada.

Regras:

- forms vivem no app de domínio quando ligados a domínio;
- `apps/web` instancia/orquestra;
- validação de campo fica no form;
- regra operacional fica em service/policy;
- form HTMX inválido retorna `422` com partial do form;
- submit convencional funciona sem JavaScript;
- Alpine.js só melhora estado local;
- erro de domínio sem campo vai para erro global;
- campos usam `form_field.html` quando aplicável.

### 14.2 Nova solicitação e edição de rascunho

MVP:

- mesma tela para criar e editar rascunho;
- submit convencional funciona sem JavaScript;
- HTMX pode melhorar lookup, validação e feedback;
- persistência por substituição completa;
- Django Form/FormSet ou equivalente no app de domínio;
- service valida domínio e salva;
- `422` re-renderiza form;
- Alpine.js só estado local pequeno.

Edição incremental item-a-item via HTMX exige decisão posterior.

### 14.3 Lookups operacionais

Use HTMX server-rendered por padrão.

Regras:

- endpoint retorna partial HTML, não JSON, para tela server-rendered;
- mínimo de 3 caracteres;
- resultado curto;
- só entidades ativas e autorizadas;
- sem dados sensíveis extras no DOM;
- empty/loading/error explícitos;
- teclado e leitor de tela suportados;
- Alpine.js só disclosure/seleção visual local.

### 14.4 Detalhe canônico

Detalhe de solicitação é rota canônica única:

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

Action panel muda por contexto, papel, permissão e estado. Dados vêm de context builder. Template não decide autorização.

Não crie detalhes separados por jornada sem decisão explícita.

### 14.5 Ações críticas

Exemplos:

- autorizar;
- recusar;
- atender;
- cancelar requisição;
- descartar rascunho;
- movimentar estoque.

Regras:

- action panel recebe ações resolvidas do context builder;
- destrutiva usa `danger`;
- confirmação obrigatória para destrutiva/irreversível/alto impacto;
- `modal_shell.html` para confirmação rica ou form curto;
- submit HTMX retorna `200`, `204`, `403`, `409` ou `422`;
- sucesso atualiza painel/lista/detalhe e emite feedback;
- `409` mostra próxima ação recomendada;
- backend valida permissão e estado sempre.

Não use browser `confirm()` como padrão.

## 15. Segurança frontend

Checklist obrigatório:

- autoescape Django ligado;
- sem `|safe` sem decisão explícita, sanitização e justificativa;
- conteúdo de usuário renderizado como texto;
- JSON via `json_script` ou mecanismo seguro;
- sem JSON manual em template;
- sem dados sensíveis no DOM;
- sem scripts inline soltos;
- sem `onclick`, `onchange`, `onload`;
- CSRF em HTMX mutável;
- `hx-headers` com JSON estático seguro ou helper aprovado;
- não usar `javascript:` ou `js:` em `hx-headers`;
- redirects HTMX apenas internos e validados;
- autorização sempre no backend;
- Alpine.js sem regra de negócio;
- `x-html` proibido com conteúdo vindo do backend/usuário;
- links externos com `target="_blank"` usam `rel="noopener noreferrer"`;
- HTMX não chama rotas externas;
- CSP planejada desde início, podendo começar report-only.

Erros:

- nunca mostrar stack trace, exception class, SQL, payload interno ou policy interna;
- quando houver `trace_id`, exibir como `Código de suporte`;
- `500` mostra mensagem genérica + `trace_id`;
- `403` não revela dados do recurso;
- `404` não confirma existência sensível;
- `409` mostra conflito e próxima ação;
- logs backend carregam mesmo `trace_id`.

## 16. Testes obrigatórios

### 16.1 Página completa

Teste:

- `GET` por usuário autorizado retorna `200`;
- template correto;
- contexto essencial;
- targets HTMX oficiais;
- regiões `aria-live`;
- navegação;
- ações visíveis conforme permissão;
- ações proibidas ausentes;
- empty state;
- atributos básicos de acessibilidade.

### 16.2 Action HTMX

Teste:

- request HTMX válida retorna `200` ou `204`;
- partial correta;
- headers HTMX esperados;
- target/swap compatíveis;
- form inválido retorna `422`;
- erros por campo e erro global;
- usuário sem permissão recebe `403`;
- sessão expirada recebe `401` com `HX-Redirect` ou `HX-Refresh`;
- conflito retorna `409`;
- endpoint não retorna página completa quando deveria retornar partial;
- endpoint não injeta login dentro de partial.

### 16.3 Acessibilidade

Teste quando aplicável:

- labels;
- `aria-invalid`;
- `aria-describedby`;
- `aria-live`;
- modal com `role="dialog"` e `aria-modal`;
- botões com nome acessível;
- submit com `type`;
- navegação com `aria-label`;
- erro semanticamente associado.

### 16.4 Playwright obrigatório quando

Use Playwright para:

- fluxo crítico;
- modal com submit;
- HTMX + Alpine.js;
- múltiplos swaps;
- atualização parcial de tabela;
- redirect pós-sucesso;
- evento HTMX consumido no frontend;
- aprovação/rejeição;
- movimentação de estoque;
- operação destrutiva;
- mudança de permissão;
- regressão já identificada;
- gate de lançamento.

Caso contrário, Django test client + assertions HTML/HTMX é o mínimo.

## 17. Sequência de delivery

### 17.1 PR1 — Fundação mínima

PR1 deve criar:

- `apps/web`;
- `apps/web/urls.py`;
- `apps/web/htmx.py`;
- `apps/web/navigation.py`;
- `apps/web/views/`;
- layouts `base.html`, `app_shell.html`, `auth_shell.html` quando aplicável;
- shell com header, navegação, sidebar desktop, drawer mobile, `global-feedback`, `global-errors`, `modal-root`, `main-content`;
- Tailwind v4 CSS-first;
- `styles.css` e `dist/app.css`;
- scripts `css:dev` e `css:build`;
- includes oficiais iniciais;
- helpers HTMX;
- navegação base;
- página técnica simples para validar shell/assets;
- testes de contrato da fundação.

PR1 não deve conter:

- fluxo operacional completo;
- regra de negócio em `apps/web`;
- query complexa em view;
- template em app de domínio;
- Tailwind CDN;
- script inline;
- componente genérico complexo.

### 17.2 PR2 — Primeira jornada real

PR2 implementa primeira jornada real, recomendada:

- `Minhas solicitações`;
- categoria `mobile-primary`.

PR2 deve validar:

- shell;
- navegação por papel;
- layout responsivo;
- cards/lista mobile;
- empty state;
- permissões simples;
- partials HTMX;
- testes de contrato;
- ajustes pequenos em tokens/recipes/componentes.

Não reabra arquitetura salvo bloqueio real.

### 17.3 Depois de PR1 e PR2

Ordem recomendada:

1. Jornada `mobile-primary` simples.
2. Jornada com formulário HTMX e `422`.
3. Jornada com aprovação/rejeição e `403`.
4. Jornada com conflito de domínio `409`.
5. Jornada `desktop-optimized` de Almoxarifado.
6. Fluxos críticos com Playwright antes de gate.

Não implemente jornada `desktop-optimized` de Almoxarifado antes de foundation + uma jornada real validarem shell, Tailwind, HTMX, componentes, segurança, acessibilidade e testes.

## 18. Padrões proibidos globais

Nunca faça:

- templates em `apps/<domain>/templates/`;
- `base.html` duplicado;
- layout paralelo;
- Tailwind CDN;
- CSS paralelo;
- editar `dist/app.css` manualmente;
- `tailwind.config.js` sem decisão técnica explícita;
- classes Tailwind dinâmicas;
- script inline solto;
- `onclick`, `onchange`, `onload`;
- `|safe` sem decisão;
- `x-html` inseguro;
- regra de negócio em template;
- query complexa em `apps/web`;
- autorização no frontend;
- HTMX sem contrato;
- endpoint mutável sem CSRF;
- login injetado em partial;
- componente genérico com API grande;
- `table.html` genérico no MVP;
- `card.html` genérico no MVP;
- navegação montada no template;
- hover-only para action;
- modal sem foco;
- formulário sem label;
- erro sem associação semântica;
- Playwright usado como substituto de contrato HTML/HTMX mínimo;
- PR frontend sem handoff.

## 19. Critério de aceite global

Antes de concluir issue frontend, agente deve garantir:

- [ ] Frontend Handoff Contract preenchido;
- [ ] paths oficiais usados;
- [ ] categoria responsiva declarada;
- [ ] templates/partials corretos;
- [ ] regra de domínio isolada em selectors/services/policies/forms/context;
- [ ] views em `apps/web` finas;
- [ ] HTMX com contrato;
- [ ] Alpine.js local apenas;
- [ ] componentes oficiais usados quando aplicável;
- [ ] novo componente tem contrato fino, se criado;
- [ ] acessibilidade declarada e implementada;
- [ ] foco e `aria-live` definidos quando houver interação dinâmica;
- [ ] segurança frontend respeitada;
- [ ] navegação alterada só via context builder;
- [ ] testes mínimos passando;
- [ ] Playwright incluído quando obrigatório;
- [ ] fora de escopo respeitado;
- [ ] `git diff --check` limpo.
