# Contratos de API — WMS-SAEP

Este documento define o padrão obrigatório para endpoints HTTP do WMS-SAEP.

A API formal deve ser versionada em `/api/v1/`, implementada com Django REST Framework e documentada com drf-spectacular. Nenhum endpoint novo ou alterado deve ser considerado completo sem contrato explícito de autenticação, autorização, entrada, saída, status HTTP, erros, paginação/filtros quando aplicável e schema OpenAPI.

## 1. Padrão geral

Decisões base:

- autenticação padrão por sessão Django com CSRF;
- autorização geral via `permission_classes`;
- autorização contextual centralizada em `policies.py` ou equivalente;
- views e ViewSets finos;
- regras de negócio em `services.py` ou módulos claros de use case;
- respostas de sucesso sem envelope global;
- listas sempre paginadas com envelope padronizado;
- erros sempre no envelope definido neste documento;
- filtros tipados com `django-filter`;
- códigos técnicos de erro em inglês e mensagens em PT-BR.

Token, JWT ou autenticação mista ficam fora da primeira versão. Só devem ser adotados quando houver consumidor que não use sessão de navegador com segurança, como app mobile, frontend dedicado em outro domínio, CLI, integração externa ou consumo máquina-a-máquina.

## 2. Checklist obrigatório por endpoint

Todo endpoint deve declarar:

- autenticação: padrão sessão Django, ou override justificado;
- autorização geral: `permission_classes`;
- autorização contextual: policy chamada pela view e pelo service em escritas;
- entrada: serializer específico de input quando houver body;
- saída: serializer específico de output;
- status HTTP esperados;
- erros possíveis usando o envelope comum;
- paginação, filtros, busca e ordenação quando for lista;
- schema OpenAPI via `@extend_schema`.

Padrão de nomes de serializers:

- `XListOutputSerializer`;
- `XDetailOutputSerializer`;
- `XCreateInputSerializer`;
- `XUpdateInputSerializer`;
- `XActionInputSerializer`;
- `XActionOutputSerializer`, quando a ação não retornar o recurso principal.

Serializers validam formato, tipos, coerência local do payload e representação. Regras críticas de domínio, transições de estado, autorização contextual e mutações transacionais pertencem aos services/policies.

## 3. Respostas de sucesso

Endpoints de detalhe retornam o recurso diretamente, sem envelope:

```json
{
  "id": 1,
  "name": "Material de exemplo"
}
```

Padrão de status:

- `GET list`: `200` com envelope de paginação;
- `GET detail`: `200` com objeto direto;
- `POST create`: `201` com objeto criado;
- `PUT` ou `PATCH`: `200` com objeto atualizado;
- ações de domínio, como enviar, autorizar, recusar e atender: `200` com o recurso ou resultado atualizado;
- `DELETE` ou descarte real permitido: `204` sem body.

Qualquer exceção a esse padrão deve ser documentada no `@extend_schema`, nos testes de contrato e, quando afetar contrato público, no documento de domínio ou backlog correspondente.

### 3.1. `GET /api/v1/requisitions/mine/`

Contrato da lista pessoal usada por `Minhas requisições` no frontend do piloto:

- autenticação: sessão Django padrão;
- autorização geral: usuário autenticado;
- autorização contextual: `queryset_requisicoes_pessoais()`;
- escopo:
  - em `rascunho`: apenas `criador_id = user.id`;
  - fora de `rascunho`: `criador_id = user.id OR beneficiario_id = user.id`;
  - após `envio`, o beneficiário passa a ver a requisição; se houver retorno para `rascunho`, perde o acesso novamente;
  - nota: a formulação anterior `criador_id = user.id OR beneficiario_id = user.id` sem exceção para `rascunho` estava incorreta.
- sem ampliação por papel operacional, setor responsável, Almoxarifado ou suporte/admin;
- entrada: sem body;
- query params: `page`, `page_size`, `search` e `status`;
- saída: `200` com envelope paginado de `RequisicaoListOutputSerializer`;
- erros esperados: `403 not_authenticated` para sessão ausente ou expirada e `403 permission_denied` quando o usuário autenticado não puder acessar a rota.

### 3.2. `POST /api/v1/requisitions/{id}/fulfill/`

Contrato do atendimento de requisição autorizada:

- autenticação: sessão Django padrão;
- autorização geral: usuário autenticado;
- autorização contextual: `queryset_requisicoes_visiveis()` na view e `pode_atender_requisicao()` no service;
- header obrigatório: `Idempotency-Key`, string opaca não vazia com até 128 caracteres;
- escopo da idempotência: usuário autenticado, endpoint `requisitions_fulfill`, requisição e hash canônico do payload validado;
- entrada: `retirante_fisico` opcional, `observacao_atendimento` opcional e `itens` opcional;
- sem `itens`: registra atendimento completo de todos os itens autorizados;
- com `itens`: cada item autorizado deve ser informado com `item_id`, `quantidade_entregue` e, quando `quantidade_entregue < quantidade_autorizada`, `justificativa_atendimento_parcial`;
- com `itens`, pelo menos um item autorizado deve ter `quantidade_entregue > 0`; payload com todos os itens zerados retorna `409 domain_conflict` e não transiciona a requisição;
- retry com o mesmo `Idempotency-Key` e payload equivalente retorna `200` com o atendimento já concluído, sem duplicar baixa de estoque, liberação de reserva, timeline ou notificações;
- reutilizar o mesmo `Idempotency-Key` com payload incompatível retorna `409 domain_conflict` e não altera estado;
- saída: `200` com `RequisicaoDetailOutputSerializer`;
- erros esperados: `400 validation_error`, `403 permission_denied`, `404 not_found` e `409 domain_conflict`;
- efeitos de domínio: quando há ao menos uma entrega `> 0`, baixa física somente da quantidade entregue, consumo da reserva entregue, liberação da reserva não entregue e status `atendida` ou `atendida_parcialmente`.

## 4. Paginação, filtros, busca e ordenação

Listas devem usar paginação padrão:

```json
{
  "count": 123,
  "page": 1,
  "page_size": 20,
  "total_pages": 7,
  "next": "http://localhost:8000/api/v1/materials/?page=2",
  "previous": null,
  "results": []
}
```

Query params padrão:

- `page`;
- `page_size`, com máximo `100`;
- `ordering`, sempre com allowlist por endpoint;
- `search`, quando busca textual fizer sentido;
- filtros tipados via `django-filter`.

Views não devem montar filtros complexos manualmente em `get_queryset()` quando um `FilterSet` simples resolver o contrato. Regras de visibilidade por usuário, setor ou papel continuam em policies/querysets controlados, não em filtros públicos.

## 5. Envelope de erro

Todo erro deve retornar:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Dados inválidos.",
    "details": {},
    "trace_id": "01HX0000000000000000000000"
  }
}
```

Campos:

- `code`: identificador estável para máquina, em inglês;
- `message`: mensagem curta para usuário ou operador, em PT-BR;
- `details`: objeto com dados estruturados do erro;
- `trace_id`: identificador de correlação para suporte e logs.

Mapeamento base:

- `400 validation_error`: payload inválido ou erro de serializer;
- `401 not_authenticated`: apenas endpoints que optam por `SessionAuthentication401` retornam `401` quando a sessão não está autenticada;
- `403 not_authenticated`: endpoints com `SessionAuthentication` padrão retornam `403` quando a sessão não está autenticada;
- `403 permission_denied`: usuário autenticado sem permissão para a ação;
- `404 not_found`: recurso inexistente ou fora do escopo visível;
- `409 domain_conflict`: estado atual impede a operação, saldo mudou, transição inválida ou regra de domínio conflitou com dados atuais;
- `500 internal_error`: erro inesperado.

Erros de campo ficam em `details` por campo. Erros de domínio ficam em `details` com dados úteis e não sensíveis, por exemplo saldo atual, status atual, ação bloqueada ou identificador do item afetado.

Para evitar vazamento de dados, objeto fora do escopo visível do usuário pode ser tratado como `404 not_found`. Quando o usuário tem acesso ao objeto, mas não pode executar a ação, usar `403 permission_denied`.

## 6. OpenAPI

Endpoints formais devem compor o schema em `/api/v1/schema/`.

Em desenvolvimento, a documentação interativa deve ficar em `/api/v1/docs/`. Em produção, Swagger/Redoc devem exigir usuário autenticado e staff, salvo decisão posterior registrada.

Todo endpoint deve usar `@extend_schema` com:

- `operation_id`;
- `tags`;
- `request`;
- `responses`;
- parâmetros de paginação, filtros, busca e ordenação quando aplicáveis;
- exemplos apenas quando ajudarem a fixar contrato crítico.

As respostas de erro comuns devem ser reutilizadas por helpers de schema, evitando duplicação manual em cada endpoint.

## 7. Bootstrap DRF de referência

A configuração base atual deve seguir esta forma:

```python
INSTALLED_APPS = [
    # ...
    "rest_framework",
    "drf_spectacular",
    "django_filters",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "apps.core.api.pagination.StandardPageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "EXCEPTION_HANDLER": "apps.core.api.exceptions.exception_handler",
}
```

Infraestrutura comum esperada em `apps/core/api/`:

- `exceptions.py`: exceções de domínio HTTP-safe e `exception_handler`;
- `pagination.py`: paginação padrão;
- `serializers.py`: serializers do envelope de erro;
- `schema.py`: helpers de OpenAPI para erros, paginação e respostas comuns.

Esses módulos são infraestrutura de API. Eles não devem conter regra de negócio de apps de domínio.

## 8. Testes obrigatórios

Para cada endpoint novo ou alterado:

- caminho feliz;
- chamada sem autenticação;
- usuário autenticado sem permissão;
- autorização contextual quando houver escopo por setor, papel ou objeto;
- input inválido com envelope de erro;
- violação de domínio com `409 domain_conflict`, quando aplicável;
- paginação, filtros, busca e ordenação para listas;
- schema OpenAPI cobrindo request, responses e status principais.

Fluxos críticos de estoque, requisição e autorização também exigem testes de service/policy e testes PostgreSQL de concorrência quando houver lock, saldo, reserva ou ledger.
