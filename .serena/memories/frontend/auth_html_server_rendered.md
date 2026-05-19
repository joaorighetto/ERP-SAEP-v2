# Frontend auth HTML server-rendered

Current status: implemented and merged.

Source tracker:
- Issue #38: https://github.com/JMZR-SAEP/WMS-SAEP/issues/38
- PR #39: https://github.com/JMZR-SAEP/WMS-SAEP/pull/39 (`feat(auth): PR3 — login e logout HTML server-rendered`)
- Merged at: 2026-05-19 20:14 UTC
- Merge commit: `4ed8e84dd45e1c437e6885f5e2996954854b1035`

Contract:
- HTML auth lives in `apps/web`, not in the DRF auth views.
- `LOGIN_URL = "/login/"` resolves to `web:login`.
- Routes: `web:login` (`/login/`), `web:logout` (`/logout/`), `web:logged_out` (`/logout/concluido/`).
- Views: `apps/web/views/auth.py` with `LoginView`, `LogoutView`, `LoggedOutView`.
- Form: `apps/users/forms.py::LoginForm` with `matricula_funcional` and `password`; authentication happens in the view using Django `authenticate()`, not in form domain validation.
- Templates: `apps/web/templates/web/pages/auth/login.html` and `logged_out.html`, both under the official `apps/web` server-rendered surface.
- Login works without JavaScript and uses Django session auth + CSRF.
- Logout is POST + CSRF; GET `/logout/` must not terminate the session and redirects safely to login.
- `next` is accepted only when internal and is validated with Django URL safety helpers before redirect.
- Authentication failure message is generic: `Matrícula funcional ou senha inválidas.` Do not reveal nonexistent user, wrong password, inactive user, or internal policy details.
- The authenticated shell exposes logout as a POST form, not as a plain GET link.

Out of scope from this slice:
- password reset, 2FA, OAuth/social login, HTMX login behavior, Playwright, and changes to DRF `AuthLoginView`/`AuthLogoutView`.

Validation baseline from the merged PR:
- `tests/web/test_auth.py` covers login/logout HTML behavior, CSRF presence, invalid/valid credentials, inactive users, safe `next`, accessibility attributes, logged-out page, and GET logout safety.
- The quick operational manual section 13 was updated after merge to mark this as implemented.