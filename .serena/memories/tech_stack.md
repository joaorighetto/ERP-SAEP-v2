# Tech stack

Current active stack for ERP-SAEP:
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

Current dependency baseline after the 2026-04-27 audit/upgrade (`d7702de chore: upgrade python dependencies`):
- Django 6.0.4, djangorestframework 3.17.1, drf-spectacular 0.29.0.
- django-filter 25.2, django-allauth 65.16.1, django-cors-headers 4.9.0.
- psycopg/psycopg-binary 3.3.3, python-dotenv 1.2.2.
- pytest 9.0.3, pytest-django 4.12.0, coverage 7.13.5, ruff 0.15.12, pre-commit 4.6.0, factory_boy 3.3.3.
- Validation passed locally: `pip check` clean and `rtk make test` with 15 passed, 1 drf-spectacular/Python 3.14 deprecation warning.

Materialization baseline:
- **Django materialization (MAT-000 to MAT-006) COMPLETED** ✅
All technical bootstrap tasks finished; functional piloto work (PIL-*) ready to begin.

Materialization included:
- MAT-000: Align documentation pre-materialization
- MAT-001: Inspect repository structure and confirm baseline
- MAT-002: Create minimal Django bootstrap (manage.py, config/, apps/)
- MAT-003: Configure settings/base/dev/test, environment, PostgreSQL via DATABASE_URL
- MAT-004: Set up smoke tests (pytest, conftest, test_bootstrap, test_api_schema)
- MAT-005: Configure DRF, OpenAPI/drf-spectacular, core API app, pagination, error handler
- MAT-006: Set up CI workflow (GitHub Actions lint + test jobs) and pre-commit hooks

Current state: Django project initialized with technical infrastructure, no domain apps.\n  - `MAT-000`: Align docs pre-materialization; close ambiguity about bootstrap approach.\n  - `MAT-001`: Inspect repo structure and confirm baseline.\n  - `MAT-002`: Create minimal Django bootstrap.\n  - `MAT-003`: Configure settings structure, environment, PostgreSQL via `DATABASE_URL`.\n  - `MAT-004`: Set up smoke tests and pytest.\n  - `MAT-005`: Configure DRF, OpenAPI/drf-spectacular, `apps/core/` technical infrastructure.\n  - `MAT-006`: Adjust CI (ruff, pytest, `manage.py check`) and pre-commit hooks.\n- Bootstrap is manual minimum, without external project generators.
- Initial settings are `config.settings.base`, `config.settings.dev`, and `config.settings.test`; do not create a separate `test_postgres` settings module.
- `config/` owns settings, URLs, ASGI/WSGI, and project bootstrap.
- `apps/core/` is technical API infrastructure only; it may host pagination, error envelope, schema helpers, and non-domain API utilities.
- `apps/users/` is not created during materialization; it is created by `PIL-BE-ACE-001`.
- PostgreSQL is configured through `DATABASE_URL`; no Docker Compose or production settings are part of the materialization backlog.

Current scope rule: frontend is not part of the active implementation scope. Work should focus on domain, persistence, authentication, authorization, APIs, technical imports, administrative/internal flows, and tests. Do not introduce server-rendered UI work, SPA frameworks, or dedicated frontend components unless a later technical decision explicitly reopens that scope.

Typing/tooling rule: mypy, django-stubs, and djangorestframework-stubs are intentionally out of the current stack and may be reconsidered later if static typing becomes an explicit project discipline.

Async rule: Celery is not in the pilot critical path, and no Redis dependency is part of the current stack definition. Keep CSV import as a reusable domain service so async infrastructure can be added later without duplicating business logic.

Production shape under consideration:
- Nginx -> Gunicorn -> Django -> PostgreSQL.
- Docker Compose or Python/systemd deployment may be chosen later and should be recorded before production deployment.

Serena project config is set to language support: python, markdown, yaml.