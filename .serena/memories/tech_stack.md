# Tech stack

Current active stack for WMS-SAEP:
- Python compatible with Django 6.
- Django 6 monolith.
- Django REST Framework for APIs.
- PostgreSQL as the required database for pilot/production behavior.
- Django ORM.
- drf-spectacular for OpenAPI schema.
- django-filter for typed list endpoint filters.
- django-allauth for auth support, with configuration deferred until access/authentication tasks.
- python-dotenv for local `.env` loading during materialization.
- django-cors-headers for conservative CORS configuration.
- pytest, pytest-django, ruff, coverage, and pre-commit as the initial quality/tooling base.
- factory_boy as the chosen standard for test data generation.

Approved pilot frontend stack:
- Django server-rendered frontend in the same repo/app surface.
- Django templates as the primary UI surface.
- `django-htmx` + HTMX for incremental interactions.
- Tailwind CSS for styling.
- Alpine.js only for small local state where HTMX alone is insufficient.
- Django session auth + CSRF for frontend auth flows.
- DRF + OpenAPI stay relevant for backend/frontend contract surfaces that remain API-based.
- The old `frontend/` SPA scaffold is removed and is not part of the active stack.

Current dependency baseline after the 2026-04-27 audit/upgrade (`d7702de chore: upgrade python dependencies`):
- Django 6.0.4, djangorestframework 3.17.1, drf-spectacular 0.29.0.
- django-filter 25.2, django-allauth 65.16.1, django-cors-headers 4.9.0.
- psycopg/psycopg-binary 3.3.3, python-dotenv 1.2.2.
- pytest 9.0.3, pytest-django 4.12.0, coverage 7.13.5, ruff 0.15.12, pre-commit 4.6.0, factory_boy 3.3.3.

Materialization baseline:
- Django materialization is complete and no longer tracked in a separate backlog file.
- Functional pilot slices now landed through requisitions, approvals, fulfillment, notifications, and related backend enablement work.

Current state: Django project initialized with technical infrastructure plus active domain apps `users`, `materials`, `stock`, `requisitions`, and `notifications`.

Backend module structure:
- `config/` -> settings, URLs, ASGI/WSGI, bootstrap.
- `apps/core/` -> API infrastructure, pagination, error envelope, schema helpers.
- `apps/users/` -> custom user, sectors, role/policy foundation.
- `apps/materials/` -> `GrupoMaterial`, `SubgrupoMaterial`, `Material`, list/search API, SCPI CSV parsing.
- `apps/stock/` -> `EstoqueMaterial`, immutable `MovimentacaoEstoque`, stock admin, initial-balance bootstrap, `StockAdapter` (implements `StockPort` from requisitions).
- `apps/requisitions/` -> models, declarative state machine, centralized policies, orchestration services, query helpers, sequences, idempotency, serializers, and thin views.
- `apps/notifications/` -> in-process event bus, notification models, domain event subscribers.

Port/Adapter pattern (ADR 0002 — Accepted):
- `StockPort` (Protocol): `apps/requisitions/ports.py`.
- `StockAdapter` (implementation): `apps/stock/adapters.py`.
- No direct requisitions <- stock circular dependency.

Initial settings are `config.settings.base`, `config.settings.dev`, and `config.settings.test`; do not create a separate `test_postgres` settings module.
- PostgreSQL is configured through `DATABASE_URL`; no Docker Compose or production settings are part of the active baseline.
- No React/Vite/TanStack frontend remains active in repo contract.

Current validation snapshot:
- `rtk make test` is still the broad backend validation default.
- Frontend server-rendered validation must be introduced incrementally with each new slice; do not assume the deleted SPA lint/build/E2E jobs still exist.

Current scope rule: frontend pilot work is now part of the active implementation scope through the approved Django templates + HTMX + Tailwind + Alpine architecture. Backend/API work, domain rules, persistence, authentication, authorization, imports, internal/admin flows, and tests remain the source-of-truth frontier. Do not resurrect a separate SPA path without an explicit new decision.

Typing/tooling rule: mypy, django-stubs, and djangorestframework-stubs are intentionally out of the current stack and may be reconsidered later if static typing becomes an explicit project discipline.

Async rule: Celery is not in the pilot critical path, and no Redis dependency is part of the current stack definition. The SCPI import path already lives in reusable services and can later be wrapped by async orchestration without duplicating domain rules.

Production shape under consideration:
- Nginx -> Gunicorn -> Django -> PostgreSQL.
- Docker Compose or Python/systemd deployment may be chosen later and should be recorded before production deployment.

Serena project config is set to language support: python, markdown, yaml.