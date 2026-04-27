# ERP-SAEP development routines
#
# Fluxo pensado para a fase atual do projeto:
# - ambiente descartável
# - bootstrap rápido
# - schema recriado com facilidade
# - limpeza agressiva de artefatos locais

# ------------------------------------------------------------------------------
# Environment
# ------------------------------------------------------------------------------

ifneq (,$(wildcard .env))
	include .env
endif

SHELL := /bin/bash
GNUMAKEFLAGS += --no-print-directory
.DEFAULT_GOAL := help

ROOT_DIR ?= $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
VENV_DIR ?= .venv
ENV_FILE ?= .env
ENV_EXAMPLE_FILE ?= .env.example
PID_FILE ?= .pid
PSQL ?= psql
UV ?= uv

PYTHON ?= $(UV) run python
MANAGE_PY ?= manage.py
DJANGO_ADMIN ?= $(PYTHON) $(MANAGE_PY)

DJANGO_SETTINGS_MODULE ?= config.settings.dev
TEST_SETTINGS_MODULE ?= config.settings.test

# Diretórios/artefatos locais que podem ser removidos sem medo
EPHEMERAL_DIRS ?= \
	.pytest_cache \
	.ruff_cache \
	htmlcov \
	staticfiles

# ------------------------------------------------------------------------------
# Fallback for unknown targets
# ------------------------------------------------------------------------------

%:
	@printf "\033[31;1mRotina não reconhecida: '%s'\033[0m\n" "$@"
	@$(MAKE) help

# ------------------------------------------------------------------------------
# Help
# ------------------------------------------------------------------------------

help: ## Mostrar rotinas disponíveis
	@printf "\033[33;1mRotinas disponíveis:\n"
	@egrep -h '\s##\s' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[37;1m%-20s\033[0m %s\n", $$1, $$2}'

# ------------------------------------------------------------------------------
# Bootstrap
# ------------------------------------------------------------------------------

prepare: ## Materializar .env a partir do exemplo
	@test -f $(ENV_FILE) || cp $(ENV_EXAMPLE_FILE) $(ENV_FILE)

init: veryclean prepare ## Recriar ambiente Python e instalar dependências
	$(UV) sync

# ------------------------------------------------------------------------------
# Project setup
# ------------------------------------------------------------------------------

setup: cleanall ## Preparar projeto do zero para desenvolvimento
	DJANGO_SETTINGS_MODULE=$(DJANGO_SETTINGS_MODULE) $(DJANGO_ADMIN) makemigrations
	DJANGO_SETTINGS_MODULE=$(DJANGO_SETTINGS_MODULE) $(DJANGO_ADMIN) migrate
	DJANGO_SETTINGS_MODULE=$(DJANGO_SETTINGS_MODULE) $(DJANGO_ADMIN) collectstatic --noinput --clear

# ------------------------------------------------------------------------------
# Cleaning
# ------------------------------------------------------------------------------

clean: ## Limpar artefatos locais e caches (sem afetar o banco)
	-rm -rf $(EPHEMERAL_DIRS)
	-rm -f $(PID_FILE)
	-find . -type d -name "__pycache__" -exec rm -rf {} +
	-find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete

cleanall: clean resetpostgres ## Limpar tudo incluindo o banco PostgreSQL
	@:

veryclean: clean cleanall ## Voltar o workspace para um estado quase "do zero"
	-rm -rf $(VENV_DIR)
	-find . -path "*/migrations/*.py" \
		-not -name "__init__.py" \
		-delete
	-find . -path "*/migrations/*.pyc" -delete

# Reset agressivo do PostgreSQL para simular o efeito de apagar um db.sqlite3
# Requer DATABASE_URL disponível no ambiente/.env e o cliente psql instalado.
resetpostgres: ## Apagar schema public do PostgreSQL e recriá-lo do zero
	@test -n "$$DATABASE_URL" || (echo "DATABASE_URL não definido em $(ENV_FILE) ou no ambiente" && exit 1)
	@command -v $(PSQL) >/dev/null 2>&1 || (echo "psql não encontrado" && exit 1)
	$(PSQL) "$$DATABASE_URL" -v ON_ERROR_STOP=1 -c "DROP SCHEMA IF EXISTS public CASCADE;"
	$(PSQL) "$$DATABASE_URL" -v ON_ERROR_STOP=1 -c "CREATE SCHEMA public;"
	$(PSQL) "$$DATABASE_URL" -v ON_ERROR_STOP=1 -c "GRANT ALL ON SCHEMA public TO CURRENT_USER;"

# ------------------------------------------------------------------------------
# Extra úteis
# ------------------------------------------------------------------------------

test: ## Rodar testes com settings de teste
	DJANGO_SETTINGS_MODULE=$(TEST_SETTINGS_MODULE) $(UV) run pytest

run: ## Subir servidor de desenvolvimento
	DJANGO_SETTINGS_MODULE=$(DJANGO_SETTINGS_MODULE) $(DJANGO_ADMIN) runserver

resetdb: ## Reaplicar migrations do banco atual (sem apagar arquivos de migration)
	DJANGO_SETTINGS_MODULE=$(DJANGO_SETTINGS_MODULE) $(DJANGO_ADMIN) migrate zero --noinput
	DJANGO_SETTINGS_MODULE=$(DJANGO_SETTINGS_MODULE) $(DJANGO_ADMIN) migrate

.PHONY: help prepare init setup clean cleanall veryclean test run resetdb resetpostgres
.EXPORT_ALL_VARIABLES:
