# Plan: #82 — refactor(requisitions): renomear queries.py para data.py

## Scope

Rename `apps/requisitions/queries.py` → `apps/requisitions/data.py`.
Update all imports. Zero logic changes.

## Files touched

- `apps/requisitions/queries.py` → renamed to `apps/requisitions/data.py`
- `apps/requisitions/services.py` — update import line 6: `queries` → `data`

No other files reference `queries` module directly. Verified with:
  `rg -n --glob '!.venv' --glob '!.git' 'apps/requisitions\.queries|from .* import queries' --include="*.py"`
  → zero matches outside migrations/.

## Test strategy

- Run full suite (`rtk make test`) after rename — must stay green.
- No new tests needed: purely mechanical rename, no behavior change.

## Invariants preserved

- No domain logic touched.
- No model, serializer, view, or policy changes.

## Risks

- Low. Single import site. `git mv` preserves history.
