# Code style and conventions

General style:
- Follow existing repository patterns and documented design decisions before introducing new abstractions.
- Keep changes narrow and aligned with domain boundaries.
- Prefer services/use cases for business logic and policies for contextual authorization.
- Keep views, serializers, templates, HTMX partials, admin actions, signals, and management commands thin.
- Use explicit contracts for APIs and update OpenAPI/tests when contracts change.
- Follow `docs/design-acesso-rapido/api-contracts.md` as the canonical API contract standard.
- Add regression tests for every bug fix.

Django/DRF conventions:
- Custom auth backend for matricula login must preserve compatibility with Django standard auth (`authenticate(username=..., password=...)`, admin, sessions).
- Use DRF serializers for input validation, local payload coherence, typing, output.
- Use thin ViewSets/APIViews + explicit permissions to prevent IDOR and cross-scope access.
- Version formal endpoints under `/api/v1/`; session auth with CSRF by default.
- Do not wrap successful detail/action responses in envelope; lists use pagination envelope.
- Use standard error envelope: `{ "error": { "code", "message", "details", "trace_id" } }`.
- Use `django-filter` for typed list filters.
- Put business rules in `services.py`, contextual access rules in `policies.py`.
- For writes, services must validate profile, scope, and domain state.
- For SCPI catalogs, pair model validation with DB constraints when ORM bypass is a real risk.

Frontend conventions:
- Build pilot frontend with Django templates first.
- Use HTMX for partial submit, filtering, reload, and inline actions before considering Alpine.js.
- Use Alpine.js only for small local state such as toggle/disclosure/modal-simple behavior.
- Do not encode domain transitions, permission decisions, or contract shaping in templates or Alpine snippets.
- Do not recreate a separate SPA scaffold unless a new ADR explicitly reopens that path.
- Keep UI language aligned with domain terms from `CONTEXT.md`.

Patterns — Port/Adapter and state machine:
- Define thin domain interfaces (Protocols) as ports; implement adapters in infrastructure modules.
- Declare state machines as explicit transition tables with a single applier function, not scattered `if/elif`.
- Extract queries, sequences, idempotency, validation into focused modules; keep `services.py` for orchestration.
- Side effects (stock mutations, notifications) are explicit function calls or port invocations, not table-driven magic.

Agent/shell convention:
- Repository instruction imports `/Users/jmzr/.codex/RTK.md`; shell commands should be prefixed with `rtk`.
- If `rtk` cannot express a needed command form, use `rtk proxy <cmd>`.
