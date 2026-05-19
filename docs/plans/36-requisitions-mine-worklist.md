# Plano — #36: PR2 Minhas solicitações server-rendered

## Scope

**Muda:**
- `apps/requisitions/contexts.py` — adicionar presenter/context builder `build_requisicao_worklist_item`
- `apps/web/navigation.py` — atualizar URL `requisitions_mine` de placeholder para rota real
- `apps/web/urls.py` — adicionar rota `requisitions_mine`
- `apps/web/views/requisitions.py` — nova view fina `MinhasSolicitacoesView`
- `apps/web/templates/web/pages/requisitions/` — 7 templates
- `tests/web/test_requisitions_mine.py` — testes de contrato

**NÃO muda:**
- Contrato DRF / OpenAPI
- `apps/requisitions/policies.py` — `queryset_requisicoes_pessoais` usado como está
- `apps/requisitions/models.py`
- Shell/layout existente
- Outros componentes de `apps/web/components/`

## Arquivos tocados

| Arquivo | Ação |
|---|---|
| `apps/requisitions/contexts.py` | Adicionar presenter `build_requisicao_worklist_item` e classe `RequisicaoWorklist­Item` |
| `apps/web/navigation.py` | Trocar `reverse("web:home")` por `reverse("web:requisitions_mine")` no item `requisitions_mine` |
| `apps/web/urls.py` | Adicionar `path("minhas-solicitacoes/", ...)` |
| `apps/web/views/requisitions.py` | Criar view `MinhasSolicitacoesView` |
| `apps/web/templates/web/pages/requisitions/list.html` | Criar template de página completa |
| `apps/web/templates/web/pages/requisitions/_filters.html` | Partial: filtros HTMX |
| `apps/web/templates/web/pages/requisitions/_list.html` | Partial: resultado HTMX (cards + tabela + paginação) |
| `apps/web/templates/web/pages/requisitions/_cards.html` | Cards mobile |
| `apps/web/templates/web/pages/requisitions/_table.html` | Tabela desktop |
| `apps/web/templates/web/pages/requisitions/_empty_state.html` | Empty state contextual |
| `apps/web/templates/web/pages/requisitions/_pagination.html` | Paginação HTMX |
| `tests/web/test_requisitions_mine.py` | Testes de contrato |

## Context builder

`build_requisicao_worklist_item(req, user)` retorna dataclass com:
- `id`, `detail_url` (None por ora — sem detalhe nesta issue)
- `is_rascunho: bool`
- `numero_publico: str | None`
- `status_value: str`
- `status_label: str`
- `status_variant: str`  (neutral/info/success/warning/danger)
- `data_label: str`  (contextual pela fase)
- `is_beneficiario_terceiro: bool`
- `beneficiario_nome: str | None`
- `resumo_itens: str`  (ex: "3 itens")
- `can_view_detail: bool`  (False por ora)

Status -> variant map:
- `rascunho` -> `neutral`
- `aguardando_autorizacao` -> `info`
- `recusada` -> `danger`
- `autorizada` -> `success`
- `pronta_para_retirada_parcial` -> `warning`
- `pronta_para_retirada` -> `success`
- `retirada` -> `neutral`
- `cancelada` -> `danger`
- `estornada` -> `danger`

## View

`MinhasSolicitacoesView(LoginRequiredMixin, View)`:
- GET: `queryset_requisicoes_pessoais(user)`
- filtro `q`: busca em `numero_publico__icontains` + `observacao__icontains`
- filtro `status`: valor exato de `StatusRequisicao`
- paginar com `Django Paginator`, 20 por página
- `request.htmx` → renderizar `_list.html` (partial)
- request normal → renderizar `list.html` (página completa)
- sessão expirada via `LoginRequiredMixin` → redirect padrão Django para `/login/`

## HTMX

- target: `#requisitions-worklist`
- swap: `innerHTML`
- método: `GET`
- URL: `web:requisitions_mine`
- partial: `_list.html`
- foco após filtro: permanece no filtro ativo
- foco após paginação: início da worklist (`#requisitions-worklist`)

## Estratégia de testes

| Caso | Tipo |
|---|---|
| GET 200, template correto, shell presente | happy path |
| HTMX GET retorna partial `_list.html` | HTMX |
| Target `#requisitions-worklist` presente | HTML assertion |
| `hx-get`, `hx-target`, `hx-push-url` nos filtros/paginação | HTML assertion |
| Estado vazio (sem solicitações) | empty state |
| Estado com dados (lista com item) | dados |
| Empty state por filtro (resultados zerando) | filtered-empty |
| Unauthenticated → 302 redirect | auth |
| `aria-live`, `aria-label`, headings | acessibilidade |

## Invariantes

- Autorização via `queryset_requisicoes_pessoais` — não duplicar lógica
- View fina: sem regra de negócio
- Template passivo: sem lógica de autorização
- Nenhum dado sensível no HTML (policies brutas, modelo completo)
- Nenhuma action mutável nesta issue

## Riscos

- `detail_url` é None/`#` por ora — detalhe canônico entra em issue futura
- Filtros de texto limitados ao que o queryset atual suporta sem alterar contrato DRF
- Não alterar `queryset_requisicoes_pessoais` — wrapper/adaptação apenas no presenter
