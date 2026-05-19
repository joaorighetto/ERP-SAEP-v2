# Plan: #38 — Auth HTML server-rendered (login e logout)

## Scope

### Changes

- `apps/users/forms.py` — add `LoginForm` (matricula_funcional + password)
- `apps/web/views/auth.py` — `LoginView`, `LogoutView`, `LoggedOutView`
- `apps/web/urls.py` — routes: `web:login`, `web:logout`, `web:logged_out`
- `apps/web/templates/web/pages/auth/login.html`
- `apps/web/templates/web/pages/auth/logged_out.html`
- `apps/web/templates/web/layouts/_sidebar_content.html` — add logout button to user info block
- `tests/web/test_auth.py` — full test coverage per handoff

### Does NOT change

- `apps/users/views.py` — DRF auth views stay untouched
- `apps/users/urls.py` — DRF routes stay
- `config/settings/base.py` — `LOGIN_URL = "/login/"` already correct
- Tailwind tokens, design system
- Any domain logic (policies, services, models)

## Files touched

| File | Action | Notes |
|------|--------|-------|
| `apps/users/forms.py` | modify | append `LoginForm` after existing forms |
| `apps/web/views/auth.py` | create | `LoginView`, `LogoutView`, `LoggedOutView` |
| `apps/web/urls.py` | modify | add 3 url patterns |
| `apps/web/templates/web/pages/auth/login.html` | create | uses `auth_shell.html` + `auth_content` block |
| `apps/web/templates/web/pages/auth/logged_out.html` | create | uses `auth_shell.html` |
| `apps/web/templates/web/layouts/_sidebar_content.html` | modify | add logout `<form>` POST in user info block |
| `tests/web/test_auth.py` | create | ~25 test methods |

## Design decisions

- `auth_shell.html` already centering card on muted bg — reuse as-is, fill `{% block auth_content %}`
- `LoginForm` stays in `apps/users/` (domain layer owns auth forms)
- `LoginView` is a plain `View` (not CBV mixin) for full control over redirect logic
- `next` validated with Django's `url_has_allowed_host_and_scheme`; fallback: `web:home`
- Logout: POST-only via `<form method="post">` with CSRF; GET redirects to `web:login` (no session kill)
- Error message always generic: `"Matrícula funcional ou senha inválidas."` — no distinction
- Authenticated user hitting GET /login/ → redirect to `web:home` (no reprocess)
- Logout button in sidebar: `<form method="post" action="{% url 'web:logout' %}">` + csrf_token

## Test strategy

### Happy path
- GET /login/ → 200, correct template, form fields present, CSRF present
- POST /login/ valid creds → 302 to web:home
- POST /login/ valid creds + valid `next` → 302 to `next`
- POST /logout/ authenticated → session killed, redirect to logged_out

### Permission / auth
- GET /login/ authenticated user → 302 to web:home
- POST /login/ inactive user → 200, generic error, no session
- POST /logout/ unauthenticated → safe (no 500), redirect

### Domain violation / contract error
- POST /login/ invalid creds → 200, alert.danger present, no session created
- POST /login/ blank fields → 200, field errors present, aria-invalid present
- POST /login/ `next` = external URL → 302 to web:home (not the external URL)
- GET /logout/ → 302 to web:login, NO session kill

### Accessibility
- label elements present for both fields
- aria-invalid on field with error
- aria-describedby points to existing error element
- alert.danger in page on credential failure
- button submit has type="submit"

## Invariants

From `matriz-invariantes.md`:
- Auth always validated in backend — no frontend-only gate
- Error messages must not reveal internal state (user existence, password vs inactive)
- CSRF required on all mutating POST requests

## Risks

- `request` available in sidebar via Django's `RequestContext` — already used (`request.user.is_authenticated`). Safe to add logout form.
- `form_field.html` renders `field.value` — password field will be empty on re-render (correct; never re-populate passwords)
- `LoginForm` field name `matricula_funcional` must match `MatriculaBackend.authenticate(username=...)` call — use `username=form.cleaned_data["matricula_funcional"]`
