# Project Status — Post-Materialization

**Date:** 2026-04-27  
**Status:** Django materialization COMPLETE; piloto functional work ready to begin  
**Current branch:** main (all MAT-* PRs merged)

## What Was Accomplished

### Documentation & Planning (MAT-000)
- Aligned pre-materialization docs in `docs/design-acesso-rapido/stack.md`
- Clarified before/after/post-PIL structure
- Updated backlog references

### Repository Inspection (MAT-001)
- Confirmed baseline state
- Verified Makefile, requirements.txt, pyproject.toml, .env.example present
- Confirmed no domain apps pre-materialized (expected)

### Django Bootstrap (MAT-002)
- Created `manage.py`
- Created `config/` package (urls.py, asgi.py, wsgi.py)
- Created `config/settings/` package structure
- Created `apps/` namespace
- Django Admin enabled

### Settings & Environment (MAT-003)
- `config/settings/base.py`: shared configuration (DRF, OpenAPI, CORS, DATABASE_URL parsing)
- `config/settings/dev.py`: development overrides (DEBUG=True)
- `config/settings/test.py`: test database configuration
- `.env.example` updated for Django/API context
- `requirements.txt` with pinned versions (major ranges)
- python-dotenv, django-cors-headers added
- Dependency baseline upgraded on 2026-04-27 in commit `d7702de`: Django 6.0.4, DRF 3.17.1, drf-spectacular 0.29.0, django-filter 25.2, django-allauth 65.16.1, django-cors-headers 4.9.0, psycopg 3.3.3, pytest 9.0.3, pytest-django 4.12.0, coverage 7.13.5, ruff 0.15.12, pre-commit 4.6.0, factory_boy 3.3.3

### Smoke Tests (MAT-004)
- `tests/` directory created
- `tests/conftest.py`: pytest fixtures
- `tests/test_bootstrap.py`: 9 smoke tests (settings, URLs, Django check)
- `tests/test_api_schema.py`: 6 schema/docs smoke tests
- **All 15 tests passing** ✅

### DRF/OpenAPI Infrastructure (MAT-005)
- `apps/core/` technical app created
- `apps/core/api/pagination.py`: StandardPagination (20 items/page)
- `apps/core/api/exceptions.py`: custom exception handler with error envelope
- `apps/core/api/serializers.py`: error response serializers
- `/api/v1/schema/`: OpenAPI schema endpoint (drf-spectacular, public)
- `/api/v1/docs/`: Swagger UI endpoint (public)

### CI/CD & Linting (MAT-006)
- `.github/workflows/ci.yml`: GitHub Actions workflow
  - Job 1 (lint): ruff check + ruff format --check
  - Job 2 (test): PostgreSQL service + install deps + manage.py check + pytest
- `.pre-commit-config.yaml`: ruff hooks (check + format)
- **All CI checks passing locally** ✅

## Current State

```
Project Structure:
├── manage.py
├── config/
│   ├── settings/ (base, dev, test)
│   ├── urls.py (admin + API endpoints)
│   ├── asgi.py, wsgi.py
├── apps/
│   └── core/ (technical API infrastructure)
├── tests/ (15 smoke tests)
├── .github/workflows/ci.yml
├── .pre-commit-config.yaml
├── requirements.txt (pinned versions)
└── .env.example (Django/API context)

Tech Stack:
- Python 3.14 + Django 6.0
- PostgreSQL (DATABASE_URL parsing)
- Django REST Framework + drf-spectacular (OpenAPI)
- pytest + pytest-django (15 smoke tests passing)
- ruff (check + format) + pre-commit
- CORS configured for localhost:3000, localhost:8000

No domain apps, no migrations (ephemeral, not committed).
```

## Ready for Functional Piloto (PIL-*)

First functional task: `PIL-BE-ACE-001` — Create custom user model with matricula funcional.

All pre-conditions met:
- ✅ Django initializable
- ✅ Settings configured
- ✅ PostgreSQL ready
- ✅ DRF + OpenAPI ready
- ✅ Smoke tests passing
- ✅ CI workflow ready
- ✅ Pre-commit hooks ready
