# Architecture and domain invariants

Core architectural rule: business rules belong in `services.py` / service-use-case modules. Keep DRF views, serializers, templates, HTMX partial views, Alpine snippets, admin actions, signals, management commands, and generic helpers thin. Serializers validate input/output shape and local payload coherence, not critical domain workflow.

Authorization must be explicit and consistent. Contextual authorization should be centralized in `policies.py` or equivalent and used by both views and services. Always validate object scope/profile in services for writes, and for concurrent write paths prefer validating against the locked/reloaded object inside `transaction.atomic()` instead of the potentially stale caller instance.

Authentication invariant:
- The pilot login identifier is `matricula_funcional`.
- Custom Django auth backends must stay compatible with the standard `authenticate(username=..., password=...)` flow in addition to `USERNAME_FIELD`/explicit credential kwargs, so Django Admin, forms, and session-based flows keep working.
- Missing-user authentication paths should still execute password hashing work before returning `None` to reduce timing-based user enumeration.

Every API endpoint must follow `docs/design-acesso-rapido/api-contracts.md`: session authentication with CSRF by default, general authorization through `permission_classes`, contextual authorization through shared policies, explicit input/output serializers, explicit status codes, the standard error envelope, pagination/filtering/ordering when applicable, and OpenAPI schema coverage. Changes to API contracts require tests and schema updates.

Frontend architecture invariant:
- The active pilot frontend is Django server-rendered, not a separate SPA.
- Django templates are the primary UI surface.
- HTMX is the first choice for incremental interaction.
- Alpine.js is allowed only for small local state where HTMX alone is insufficient.
- Do not move domain rules or authorization decisions into templates, Alpine state, or ad hoc JS.
- Do not resurrect `frontend/`, React, Vite, TanStack, generated TS clients, or deleted SPA CI jobs without an explicit new architecture decision.

API response invariant:
- Successful detail/action responses return the resource or result directly, without a global success envelope.
- List responses use the standard pagination envelope with `count`, `page`, `page_size`, `total_pages`, `next`, `previous`, and `results`.
- Error responses always use `{ "error": { "code", "message", "details", "trace_id" } }`.
- Error codes are stable English machine codes; messages are PT-BR.
- Domain conflicts use HTTP 409 with code `domain_conflict`.

Stock invariants:
- `MovimentacaoEstoque` is immutable. Do not update/delete/overwrite movements; corrections must be modeled as new movements when new movement types are introduced.
- Currently implemented movement types: `SALDO_INICIAL`, `RESERVA_POR_AUTORIZACAO`, `SAIDA_POR_ATENDIMENTO`, and `LIBERACAO_RESERVA_ATENDIMENTO`.
- Stock writes use `transaction.atomic()` + `select_for_update()` for row locking. Always lock inside transaction; never pass unlocked row to service outside tx context.
- Keep `EstoqueMaterial.saldo_fisico`, `saldo_reservado`, `saldo_disponivel` consistent and prevent race conditions.
- Reservation rejects `quantidade <= 0`, revalidates available balance inside locked stock service.
- Fulfillment exit rejects `quantidade <= 0`, revalidates both balances after lock, decrements both, records `SAIDA_POR_ATENDIMENTO`.
- Partial fulfillment release rejects `quantidade <= 0`, revalidates reserved balance, preserves `saldo_fisico`, prevents `saldo_fisico < saldo_reservado_posterior`.
- Stock service shortcuts receiving locked `EstoqueMaterial` via `estoque_travado` must run inside `transaction.atomic()` block only.

Port/Adapter pattern (ADR 0002):
- `requisitions` defines `StockPort` (Protocol) in `apps/requisitions/ports.py`; `stock` implements `StockAdapter` in `apps/stock/adapters.py`.
- Three coarse-grained port methods: `aplicar_reservas_autorizacao`, `liberar_reservas_cancelamento`, `aplicar_saidas_e_liberacoes_retirada`.
- No domain objects leak from stock to requisitions via port.
- Side effects removed from transition table; stock calls stay explicit in services after transition application.
- Dependency direction: requisitions -> port/interface <- stock implements.

Requisitions module structure:
- `domain/state_machine.py`: declarative state machine with transition table and single applier function.
- `queries.py`: query helpers (load, lock, validate before mutation).
- `sequences.py`: sequence generators for public numbers, IDs.
- `idempotency.py`: payload idempotency pattern with cached result.
- `services.py`: focused business orchestration.
- `policies.py`: centralized contextual authorization checks.

Dependency direction:
`apps/core/` is technical infrastructure only and must not depend on domain apps. Domain app dependencies should remain explicit and acyclic. Notifications and other side effects must be reached by post-commit events instead of direct domain coupling.

Materials/SCPI invariants:
- `GrupoMaterial` and `SubgrupoMaterial` are structural catalogs backed by SCPI data, not freeform WMS-maintained master data.
- SCPI code fragments for group/subgroup must remain exactly 3 numeric digits and should be enforced both in model validation and with DB-level constraints.
- Manual operational mutation of SCPI-official fields such as group/subgroup codes and names should not be exposed through normal admin add/change/delete surfaces.
- Material search/list selection for requisition flows must return only active materials and include current `saldo_disponivel`.
- The SCPI import pipeline is parser/normalizer first, service orchestration second, persistence third; do not collapse critical normalization into ad hoc command logic.
- SCPI import persistence is all-or-nothing.
- Imported material names should be normalized to a single line / single-space representation before persistence.

Development environment rule: local DB and app migrations are ephemeral during this early phase. Do not commit generated app migrations. For schema/model changes, rebuild local migrations and validate against a clean local database. Generated migrations are temporary materialization artifacts, not normal deliverables.