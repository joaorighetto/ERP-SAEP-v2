# Diagnóstico de Estrutura — MAT-001

**Data:** 2026-04-27  
**Status:** Diagnóstico confirmado antes da materialização Django

## 1. Arquivos Django esperados (PRÉ-MATERIALIZAÇÃO)

### Ausentes — Devem ser criados em MAT-002 a MAT-006

| Item | Status | Nota |
|---|---|---|
| `manage.py` | ✗ Ausente | Criado em MAT-002 |
| `config/` | ✗ Ausente | Pacote criado em MAT-002 |
| `config/__init__.py` | ✗ Ausente | Criado em MAT-002 |
| `config/urls.py` | ✗ Ausente | Criado em MAT-002 |
| `config/asgi.py` | ✗ Ausente | Criado em MAT-002 |
| `config/wsgi.py` | ✗ Ausente | Criado em MAT-002 |
| `config/settings/` | ✗ Ausente | Pacote criado em MAT-003 |
| `config/settings/base.py` | ✗ Ausente | Criado em MAT-003 |
| `config/settings/dev.py` | ✗ Ausente | Criado em MAT-003 |
| `config/settings/test.py` | ✗ Ausente | Criado em MAT-003 |
| `apps/` | ✗ Ausente | Pacote criado em MAT-002 |
| `apps/__init__.py` | ✗ Ausente | Criado em MAT-002 |
| `tests/` | ✗ Ausente | Criado em MAT-004 |

## 2. Arquivos de infraestrutura (PRÉ-MATERIALIZAÇÃO)

### Presentes — Já existem

| Item | Status | Nota |
|---|---|---|
| `Makefile` | ✓ Presente | Define rotinas de desenvolvimento |
| `pyproject.toml` | ✓ Presente | Configuração de projeto e dependências Python |
| `uv.lock` | ✓ Presente | Lockfile reproduzível de dependências |
| `.env.example` | ✓ Presente | Será atualizado em MAT-003 |
| `.python-version` | ✓ Presente | Versão Python usada pelo uv e pela CI |

## 3. CI/CD (PRÉ-MATERIALIZAÇÃO)

### Presentes

| Item | Status | Nota |
|---|---|---|
| `.github/` | ✓ Presente (vazio) | Workflows serão criados em MAT-006 |

### Ausentes — Devem ser criados em MAT-006

| Item | Status | Nota |
|---|---|---|
| `.github/workflows/ci.yml` | ✗ Ausente | Criado em MAT-006 |
| `.pre-commit-config.yaml` | ✗ Ausente | Criado em MAT-006 |

## 4. Apps de domínio

### Status

✓ **Confirmado:** Não há apps de domínio materializados.

- `apps/users/` — Não existe (será criado em PIL-BE-ACE-001)
- `apps/organizational/` — Não existe
- `apps/materials/` — Não existe
- `apps/stock/` — Não existe
- `apps/requisitions/` — Não existe

## 5. Resumo de pré-condições

- ✓ Makefile funcional com rotinas recomendadas
- ✓ pyproject.toml com dependências pinadas por faixa major
- ✓ uv.lock versionado
- ✓ pyproject.toml presente
- ✓ .env.example presente (será atualizado)
- ✓ .github/ estrutura presente (vazia, pronta para CI)
- ✗ Django ainda não materializado (esperado)
- ✗ Nenhum app de domínio presente (esperado)

## 6. Conclusão

Repositório está no estado esperado **PRÉ-MATERIALIZAÇÃO**. Pronto para:

1. MAT-002: Criar bootstrap Django mínimo
2. MAT-003: Configurar settings e ambiente
3. MAT-004: Configurar testes de smoke
4. MAT-005: Configurar DRF/OpenAPI
5. MAT-006: Ajustar CI

Nenhum bloqueio encontrado. Materialização pode prosseguir.
