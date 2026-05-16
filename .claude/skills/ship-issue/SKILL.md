# ship-issue

Ship a GitHub issue end-to-end: branch → plan → implement → test → PR → CodeRabbit → done.

## Usage

```
/ship-issue <issue-number>
```

## Workflow

### 1. Read the issue

```bash
gh issue view <number> --json title,body,labels,assignees,milestone
```

Extract: title, acceptance criteria, scope constraints, linked issues.

### 2. Branch off main

```bash
git checkout main && git pull
```

Derive branch name from issue title: lowercase, no accents, no spaces, max 40 chars.
Prefix by label: `feat/`, `fix/`, `refactor/`, `chore/`, `docs/`, `test/`.

```bash
git checkout -b <prefix>/<slug>
```

**Hard stop**: never proceed if current branch is `main`. Create the branch first.

### 3. Write a plan

File: `docs/plans/<issue-number>-<slug>.md`

Sections:
- **Scope**: what changes, what does NOT change
- **Files touched**: list expected files/modules using Serena `get_symbols_overview` to map current structure
- **Test strategy**: which test files, what cases (happy path, permission denied, domain violation, contract error)
- **Invariants to preserve**: list from `docs/design-acesso-rapido/matriz-invariantes.md` relevant to the change
- **Risks**: concurrency, OpenAPI contract, stock mutations, state machine transitions

Commit the plan before implementation:

```bash
git add docs/plans/ && git commit -m "docs(<slug>): add implementation plan for #<number>"
```

### 4. Implement with Serena MCP

Navigation: use `find_symbol`, `get_symbols_overview`, `find_referencing_symbols` — never raw `Read` on code files.
Edits: use `replace_content`, `replace_symbol_body`, `insert_after_symbol`, `insert_before_symbol` — never raw `Edit`.

Order of implementation:
1. Model / schema changes (if any) → `rtk make setup` after
2. Service layer (`services.py`) — business rules only
3. Policy layer (`policies.py`) — contextual authorization
4. Serializers — input/output shape, no domain rules
5. Views / ViewSets — thin, delegate to service + policy
6. Tests — cover: happy path, unauthenticated, permission denied, contextual scope, domain conflict (409), pagination/filters for lists

Guardrails:
- Business rules → `services.py` only
- Contextual auth → `policies.py` only
- `transaction.atomic()` + `select_for_update()` for any stock/balance mutation
- Port/Adapter: stock calls via `StockPort`, never direct import of stock models in requisitions
- No direct commit to main

Commit by logical unit as you go:

```bash
git add <specific-files> && git commit -m "<type>(<scope>): <what and why>"
```

### 5. Run full test suite via RTK tee

```bash
rtk make test
```

**Do not pipe or filter output.** RTK writes full output to `~/Library/Application Support/rtk/tee/` automatically.

- If tests fail: read the tee log, identify root cause, fix, re-run. Do not retry with different flags.
- Confirm pass count matches or exceeds baseline before proceeding.
- If schema changed: confirm `rtk make frontend-gen-api` still succeeds.

### 6. Commit and push

Final commit if anything remains unstaged:

```bash
git add <specific-files> && git commit -m "<type>(<scope>): <summary>"
git push -u origin <branch>
```

### 7. Open PR targeting upstream

Fill the PR template at `.github/pull_request_template.md` in full.

```bash
gh pr create \
  --title "<type>(<scope>): <issue title>" \
  --body "$(cat .github/pull_request_template.md | ...)" \
  --base main
```

PR body must include:
- Issue reference: `Closes #<number>`
- Summary of changes
- Test evidence: pass count before/after
- Any invariants explicitly preserved or verified
- Decisions made that diverge from or extend documented contracts

### 8. Wait for CodeRabbit

Poll until CodeRabbit posts its review (usually < 3 minutes):

```bash
gh pr checks <pr-number> --watch
```

Then fetch review comments:

```bash
gh api repos/:owner/:repo/pulls/<pr-number>/comments --jq '[.[] | {id, path, line, body, user: .user.login}]'
```

Filter to CodeRabbit findings only (`user.login == "coderabbitai[bot]"`).

### 9. Address each finding

For each CodeRabbit finding:

1. **Verify**: use Serena `find_symbol` to confirm the finding references current code (line numbers drift — trust content, not line).
2. **Classify**: Critical / Major / Minor. Skip `nitpick` unless trivial.
3. **Fix**: minimal targeted change via `replace_content` or `replace_symbol_body`. Do not refactor adjacent code.
4. **Test**: add or update a test that would have caught this. Run `rtk make test` after each Critical/Major fix.
5. **Commit**:

```bash
git add <files> && git commit -m "fix(<scope>): address CodeRabbit finding — <one-line summary>"
git push
```

### 10. Reply to each review thread

For every addressed finding:

```bash
gh api repos/:owner/:repo/pulls/<pr-number>/comments/<comment-id>/replies \
  -f body="Fixed in <commit-sha>. <one-line explanation of what changed and why.>"
```

For skipped findings (nitpick / out-of-scope / disagreed):

```bash
gh api ... -f body="Acknowledged. <reason for skipping>."
```

After all threads replied, re-run full suite one final time and confirm green:

```bash
rtk make test
```

---

## Blockers requiring human decision

Stop and surface clearly if:
- Issue scope is ambiguous (contradicts `docs/design-acesso-rapido/` or invariant matrix)
- Test suite was already failing before implementation
- CodeRabbit finding requires a contract change (OpenAPI, serializer output shape, error codes)
- A Critical finding cannot be fixed without expanding scope beyond the issue
- Migration strategy is unclear (schema change touches existing data)

Format blocker as:

```
BLOCKER: <one-line summary>
Context: <what was attempted>
Decision needed: <specific question>
```

## Constraints

- Never commit to `main`
- Always run full suite before opening PR
- Never use raw `Read`/`Edit` on code files — use Serena MCP
- Always consult Context7 before implementing against Django/DRF/frontend libs
- OpenAPI contract changes require `rtk make frontend-gen-api` and updated tests
- Stock/balance mutations require `transaction.atomic()` + `select_for_update()`
- `docs/plans/<file>.md` must exist before first implementation commit
