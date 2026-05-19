# Plano — Issue #34: PR1 Fundação Mínima do Frontend Server-Rendered

## Scope

**Inclui:**
- `apps/web` (app Django completo)
- `apps/web/htmx.py` — helpers HTMX mínimos
- `apps/web/navigation.py` — allowlist por papel + context builder
- `apps/web/views/home.py` — página técnica de validação
- `apps/web/urls.py` — rotas HTML com `app_name = "web"`
- Layouts: `base.html`, `app_shell.html`, `auth_shell.html`
- Componentes: `button.html`, `badge.html`, `alert.html`, `form_field.html`, `empty_state.html`, `pagination.html`, `modal_shell.html`
- Página: `pages/home.html`
- Tailwind v4 CSS-first: `styles.css`, `dist/app.css` (gerado por build)
- `package.json` com scripts `css:dev` e `css:build`
- Makefile: targets `css-build`, `css-dev`
- Ajuste em `.gitignore`: ancorar `dist/` → `/dist/` para não bloquear `apps/web/static/web/dist/`
- `config/settings/base.py`: `apps.web`, `django_htmx`, `HtmxMiddleware`, `STATICFILES_DIRS`, `LOGIN_URL`
- `config/urls.py`: include `apps.web.urls`
- `pyproject.toml`: add `django-htmx`
- `tests/web/`: testes de contrato da fundação

**Não inclui (fora de escopo):**
- Login/logout HTML completo
- Minhas solicitações / qualquer jornada operacional
- Worklists, forms de requisição
- Tabelas, cards operacionais
- Playwright
- Templates em apps de domínio

## Files touched

```text
# Novos
apps/web/__init__.py
apps/web/apps.py
apps/web/urls.py
apps/web/htmx.py
apps/web/navigation.py
apps/web/views/__init__.py
apps/web/views/home.py
apps/web/templates/web/layouts/base.html
apps/web/templates/web/layouts/app_shell.html
apps/web/templates/web/layouts/auth_shell.html
apps/web/templates/web/components/button.html
apps/web/templates/web/components/badge.html
apps/web/templates/web/components/alert.html
apps/web/templates/web/components/form_field.html
apps/web/templates/web/components/empty_state.html
apps/web/templates/web/components/pagination.html
apps/web/templates/web/components/modal_shell.html
apps/web/templates/web/pages/home.html
apps/web/static/web/src/styles.css
apps/web/static/web/dist/app.css
apps/web/static/web/js/.gitkeep
package.json
tests/web/__init__.py
tests/web/test_foundation.py

# Modificados
.gitignore
pyproject.toml
config/settings/base.py
config/urls.py
Makefile
```

## Design system

- Estilo: Accessible & Ethical (WCAG AAA)
- Paleta: navy `#0F172A` primário, azul `#0369A1` brand/CTA, `#F8FAFC` fundo
- Tipografia: `Fira Sans` body + `Fira Code` mono (preciso, técnico, institucional)
- Tokens: definidos via `@theme` no Tailwind v4

## Test strategy

- `GET /` com usuário autenticado → 200, template `web/pages/home.html`
- `GET /` sem sessão → redirect para login
- Shell contém `#main-content`, `#global-feedback`, `#global-errors`, `#modal-root`
- Skip link existe
- `aria-live` em regiões de feedback
- `<nav aria-label="Navegação principal">` presente
- CSS compilado referenciado na página
- Navegação renderiza itens por papel (solicitante, chefia, almoxarifado, admin)
- Usuário sem papel não vê itens restritos
- Helpers HTMX: `render_htmx`, `htmx_redirect`, `htmx_session_expired` produzem respostas corretas

## Invariants

- Nenhuma regra de negócio em `apps/web`
- Nenhuma query em view (view é thin)
- Navegação vem de `navigation.py`, não de template
- CSRF configurado para HTMX mutável (via `hx-headers`)
- Sem `|safe` sem decisão explícita
- Sem script inline solto

## Risks

- `.gitignore` tem `dist/` não ancorado → bloqueia commit de `dist/app.css`; fix: ancorar para `/dist/`
- `django-htmx` não existe no `pyproject.toml` → add dependência + reinstalar
- Tailwind v4 toolchain não existe → add `package.json` com `@tailwindcss/cli`
- `STATICFILES_DIRS` não configurado → Django não encontra static da app
