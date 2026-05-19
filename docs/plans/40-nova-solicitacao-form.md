# Plan — Issue #40: Nova solicitação — formulário, rascunho e envio para autorização

## Scope

**Changes:**
- `apps/requisitions/forms.py` (NEW) — `RequisicaoRascunhoForm`, `ItemRequisicaoForm`, `ItemRequisicaoFormSet`
- `apps/materials/selectors.py` (NEW) — `buscar_materiais_para_requisicao`
- `apps/users/selectors.py` (NEW) — `buscar_beneficiarios_no_escopo`
- `apps/web/views/requisitions.py` (MODIFY) — add `RequisicaoCreateView`, `RequisicaoEditView`, `material_search_view`, `requisition_item_add_view`, `requisition_send_view`
- `apps/web/urls.py` (MODIFY) — add 5 new routes
- `apps/web/templates/web/pages/requisitions/form.html` (NEW)
- `apps/web/templates/web/pages/requisitions/_form_body.html` (NEW)
- `apps/web/templates/web/pages/requisitions/_item_row.html` (NEW)
- `apps/web/templates/web/pages/requisitions/_material_results.html` (NEW)
- `apps/web/templates/web/pages/requisitions/_beneficiary_results.html` (NEW)
- `apps/web/navigation.py` (MODIFY) — add "Nova solicitação" item
- `apps/web/static/web/js/htmx-alpine.js` (NEW) — Alpine.js reinit after HTMX swaps
- `apps/web/templates/web/layouts/base.html` (MODIFY) — load htmx-alpine.js
- `tests/web/test_requisition_form.py` (NEW)

**Does NOT change:**
- Domain services (`criar_rascunho_requisicao`, `atualizar_rascunho_requisicao`, `enviar_para_autorizacao`)
- Domain policies (already exist)
- DRF serializers / API contracts
- OpenAPI schema (no new DRF endpoints)
- Models or migrations

## Files touched

| File | Action | Purpose |
|---|---|---|
| `apps/requisitions/forms.py` | CREATE | Form + formset for draft creation/editing |
| `apps/materials/selectors.py` | CREATE | Material search for requisition lookup |
| `apps/users/selectors.py` | CREATE | Beneficiary search scoped by creator role |
| `apps/web/views/requisitions.py` | MODIFY | New views for create/edit/send/lookup |
| `apps/web/urls.py` | MODIFY | 5 new routes |
| `apps/web/templates/web/pages/requisitions/form.html` | CREATE | Full page |
| `apps/web/templates/web/pages/requisitions/_form_body.html` | CREATE | HTMX 422 re-render target |
| `apps/web/templates/web/pages/requisitions/_item_row.html` | CREATE | HTMX add-row partial |
| `apps/web/templates/web/pages/requisitions/_material_results.html` | CREATE | HTMX search results |
| `apps/web/templates/web/pages/requisitions/_beneficiary_results.html` | CREATE | HTMX beneficiary results |
| `apps/web/navigation.py` | MODIFY | "Nova solicitação" nav item |
| `apps/web/static/web/js/htmx-alpine.js` | CREATE | Alpine reinit bridge |
| `apps/web/templates/web/layouts/base.html` | MODIFY | Load htmx-alpine.js |
| `tests/web/test_requisition_form.py` | CREATE | Contract tests |

## Routes

| Name | Method | Path | View |
|---|---|---|---|
| `web:requisition_create` | GET, POST | `/requisicoes/nova/` | `RequisicaoCreateView.as_view()` |
| `web:requisition_edit` | GET, POST | `/requisicoes/<int:pk>/editar/` | `RequisicaoEditView.as_view()` |
| `web:requisition_send` | POST | `/requisicoes/<int:pk>/enviar/` | `requisition_send_view` |
| `web:material_search` | GET | `/requisicoes/materiais/buscar/` | `material_search_view` |
| `web:requisition_item_add` | GET | `/requisicoes/item/adicionar/` | `requisition_item_add_view` |

## HTMX contracts

### material_search_view
- GET `?q=<str>&idx=<int>`
- Returns `_material_results.html` (200) with list of matching materials
- Alpine `@click` on each result dispatches `material-selected` event to parent row
- Empty if `len(q) < 3` or no results

### requisition_item_add_view
- GET `?total=<int>`
- Returns `_item_row.html` for new index = `total`
- `beforeend` into `#item-rows-container`

### POST create/edit (422)
- HTMX request: returns `_form_body.html` (422) via `htmx_validation_error`
- Non-HTMX request: returns full `form.html` (422)
- Success: `HX-Redirect` to `web:requisitions_mine` (HTMX) or `redirect()` (non-HTMX)

## Test strategy

**Happy paths:**
- GET create → 200, correct template, fields present
- POST create valid (1 item) → draft created, redirect
- POST create valid with `acao=enviar` → draft created + sent to auth, redirect
- GET edit as criador → 200, form pre-filled
- POST edit valid → draft updated, redirect
- POST send → sent to auth, redirect
- HTMX material_search → 200, partial, results list
- HTMX item_add → 200, `_item_row.html`, correct index

**Permission denied:**
- GET create unauthenticated → redirect to login
- SOLICITANTE POST with beneficiario ≠ self → 403/422
- Non-criador GET edit → 404
- Non-criador POST edit → 404

**Domain violations:**
- POST create no items → 422 with `aria-invalid`
- POST create with empty `quantidade_solicitada` → 422 with field error
- POST create with invalid material_id → 422 or domain error

**Contract:**
- 422 response has `aria-invalid` in content
- 422 response has `aria-describedby` in content
- Templates have correct `data-testid` attributes
- Navigation shows "Nova solicitação" for SOLICITANTE, CHEFE_SETOR, ALMOXARIFADO roles

## Invariants

| ID | Relevant check |
|---|---|
| PER-01 | SOLICITANTE creates only for self — policy checked in service AND view |
| PER-02 | AUXILIAR_SETOR: only own sector beneficiaries |
| PER-07 | Requisition sector = beneficiário sector, not criador sector |
| PER-08 | View and service call same policy |
| REQ-01 | Service creates draft status — never view-managed |
| REQ-05 | At least one item — validated in form + service |
| EST-08 | Divergent material blocked — selector filters it out (UI hint); service enforces |
| EST-10 | Inactive material blocked — selector AND service |

## Risks

- **Formset with HTMX add-row**: `TOTAL_FORMS` management field must be updated client-side when adding rows. Passing current count via `?total=N` query param and returning the new row with correct `form-N-*` field names handles this. The management field hidden input is updated via OOB or Alpine.js.
- **Alpine init after HTMX swap**: `_material_results.html` contains Alpine `@click` buttons. HTMX injects them into the DOM after Alpine has initialized. `htmx-alpine.js` bridges this by calling `Alpine.initTree(target)` on `htmx:afterSwap`.
- **Beneficiary for SOLICITANTE**: hidden field with `request.user.pk` — validated server-side in `pode_criar_requisicao_para`. Not trusted blindly.
- **Material saldo in-flight**: UI selector shows available materials at search time. Service re-validates on submit with domain conflict error if saldo changed.
- **No model changes**: zero migration risk.
