

# Stack Técnica — WMS-SAEP

## 1. Visão geral

O WMS-SAEP será implementado como uma aplicação web monolítica baseada em Django.

A stack foi escolhida para favorecer:

- desenvolvimento rápido do piloto;
- regras de negócio centralizadas no backend;
- contratos HTTP claros para APIs;
- backend como fonte de verdade de domínio e contratos;
- implantação em servidor próprio;
- segurança transacional para estoque e requisições.

## 2. Backend

Stack principal:

- Python compatível com Django 6.
- Django 6.
- PostgreSQL.
- Django ORM.
- Django REST Framework.
- drf-spectacular.
- django-filter.
- django-allauth.

O sistema deve priorizar uma arquitetura monolítica Django com backend/API-first, mantendo regras de negócio no backend e contratos HTTP explícitos.

## 3. Frontend

O frontend do piloto faz parte do escopo ativo do projeto.

Diretriz atual:

- usar Django server-rendered como superfície principal do piloto;
- usar `django-htmx` para interações incrementais e atualização parcial de tela;
- usar Tailwind CSS para styling utilitário;
- usar Alpine.js apenas onde HTMX não resolver a interação com simplicidade suficiente;
- manter o backend Django como fonte de verdade para domínio, autenticação, autorização e OpenAPI;
- usar sessão Django com CSRF para autenticação;
- tratar o frontend como interface operacional do piloto, não como frente paralela de administração genérica;
- reconstruir a infraestrutura do frontend sem reaproveitar a SPA anterior.

Stack prevista para o frontend do piloto:

- Django templates;
- `django-htmx`;
- HTMX;
- Tailwind CSS;
- Alpine.js;
- sessão Django com CSRF;
- DRF + OpenAPI como contrato dos fluxos que continuarem expostos por API.

O detalhe operacional da arquitetura do frontend está em `docs/design-acesso-rapido/frontend-arquitetura-piloto.md`, e a decisão macro está registrada em `docs/adr/0009-frontend-piloto-django-htmx.md`.

Estado atual do reset:

- a fundação SPA anterior foi descartada;
- o diretório `frontend/` deixa de ser parte da stack ativa;
- os comandos `frontend-*` do `Makefile` deixam de ser entrypoints oficiais;
- a nova infraestrutura server-rendered será reintroduzida incrementalmente no próprio Django.

## 4. Django REST Framework

Django REST Framework faz parte da stack atual e deve ser usado para endpoints de API.

Diretrizes:

- usar serializers para validação de entrada, tipos, coerência local do payload e representação de saída;
- manter ViewSets e APIViews finos;
- concentrar regra de domínio crítica em services ou use cases;
- usar permissions para acesso geral e escopo de objeto quando aplicável;
- versionar endpoints sob `/api/v1/` quando estabilizados para consumo público ou interno formal;
- manter schema com drf-spectacular coerente com os contratos implementados;
- usar `django-filter` para filtros tipados em endpoints de lista;
- cobrir mudanças de contrato de API com testes.

Nenhum endpoint novo ou alterado deve ser considerado completo sem definição clara de autenticação, autorização, serializer de entrada, serializer de saída, permissões por papel e escopo, códigos de status esperados, formato de erro, paginação, filtros e ordenação quando aplicáveis.

O padrão canônico de contratos HTTP, respostas de sucesso, envelope de erro, paginação, filtros, autenticação e OpenAPI está em `docs/design-acesso-rapido/api-contracts.md`.

## 5. Banco de dados

O banco principal será PostgreSQL desde o início.

PostgreSQL é obrigatório para o piloto real porque o WMS-SAEP depende de:

- transações confiáveis;
- integridade relacional;
- locks de linha;
- controle de concorrência na reserva de estoque;
- relatórios operacionais;
- auditoria e histórico.

SQLite não deve ser usado para ambiente de piloto real ou produção.

Operações críticas de estoque devem usar transações atômicas, especialmente:

- autorização de requisição;
- reserva de estoque;
- atendimento e baixa de estoque;
- liberação de reserva;
- devolução;
- saída excepcional;
- estorno;
- importação CSV que altere materiais ou saldos.

Quando houver risco de concorrência sobre o mesmo estoque, usar bloqueio transacional adequado, como `select_for_update()`.

## 6. Autenticação e usuários

A autenticação será local, usando matrícula funcional e senha.

O projeto deve usar usuário customizado desde o início.

Diretriz recomendada:

- usar a matrícula funcional como identificador de login;
- manter matrícula única;
- não manter CPF como campo cadastral permanente;
- não manter telefone como campo cadastral permanente;
- usar os mecanismos de senha, sessão e permissões do Django sempre que possível.

O modelo de usuário deve estar alinhado às regras de `docs/design-acesso-ocasional/modelo-dominio-regras.md` e aos critérios de aceite de permissões.

## 7. Importação SCPI CSV

A importação SCPI CSV já faz parte do baseline atual como serviço de domínio reutilizável.

Implementação atual:

- `apps/materials/csv_parser.py`: parser/normalização do CSV SCPI;
- `apps/materials/services.py`: orquestração da carga inicial;
- `apps/stock/services.py`: registro de saldo inicial;
- `apps/materials/management/commands/importar_scpi.py`: superfície técnica via comando de management.

O mesmo núcleo de importação deve continuar reutilizável por:

- comando de management;
- endpoint técnico/autenticado, se necessário no futuro;
- task assíncrona futura, se necessário.

Escopo atual entregue:

- leitura de CSV SCPI em UTF-8 com BOM e separador `;`;
- reconstrução de registros lógicos com continuação em múltiplas linhas;
- criação de grupo, subgrupo e material a partir da carga inicial;
- criação de `EstoqueMaterial`;
- registro transacional de `MovimentacaoEstoque` do tipo `SALDO_INICIAL`.

Escopo ainda futuro, se o produto realmente precisar:

- pré-visualização de importação;
- confirmação explícita de alertas;
- histórico operacional de importações;
- reimportação com atualização controlada de saldo/catálogo.

## 8. Tarefas assíncronas

Celery não faz parte da stack atual e não é obrigatório no piloto.

A decisão inicial é:

- não colocar Celery no caminho crítico do piloto;
- manter a importação CSV como serviço reutilizável;
- permitir que Celery seja adicionado depois sem reescrever a regra de importação.

Usar processamento síncrono quando:

- a carga for controlada;
- o arquivo CSV for pequeno ou médio;
- o processamento não causar timeout;
- a operação for executada por usuário técnico ou superusuário.

Considerar infraestrutura assíncrona dedicada no futuro quando:

- arquivos CSV ficarem grandes;
- importações começarem a causar timeout;
- houver reimportações frequentes;
- relatórios pesados precisarem ser gerados fora do ciclo HTTP;
- houver necessidade de tarefas agendadas;
- houver notificações externas futuras.

Se Celery ou equivalente for adotado no futuro, ele deve processar tarefas de infraestrutura, não conter regra de negócio duplicada.

## 9. Infraestrutura

O WMS-SAEP rodará em servidor próprio.

Arquitetura recomendada de produção:

```text
Nginx
  -> Gunicorn
    -> Django
      -> PostgreSQL
```

Componentes esperados:

- Nginx como reverse proxy.
- Gunicorn como servidor WSGI.
- PostgreSQL como banco de dados.
- Serviço Django isolado.
- HTTPS sempre que possível.
- Variáveis sensíveis fora do repositório.
- Logs de aplicação e servidor.

Docker Compose pode ser usado para desenvolvimento e também para produção, se a equipe decidir operar o servidor dessa forma.

Alternativa aceitável em produção:

- ambiente Python gerenciado no servidor;
- Gunicorn controlado por systemd;
- PostgreSQL instalado no servidor;
- Nginx como proxy.

A decisão final entre Docker Compose em produção ou systemd deve ser registrada antes da implantação.

## 10. Backups

Backups devem ser tratados como requisito operacional desde o início.

Obrigatório para piloto real e produção:

- backup automático diário do PostgreSQL;
- política de retenção definida;
- teste periódico de restauração;
- backup dos arquivos enviados, especialmente CSVs importados;
- documentação do procedimento de restauração.

O sistema não deve ser considerado pronto para uso real sem rotina mínima de backup e restauração testada.

## 11. Qualidade de código

Ferramentas recomendadas:

- uv para gerenciamento de ambiente, dependências e lockfile;
- pytest;
- pytest-django;
- ruff;
- coverage;
- pre-commit;
- factory_boy para dados de teste.

Diretrizes:

- escrever testes para regras de negócio críticas;
- priorizar testes de domínio e transições de status;
- testar concorrência de reserva de estoque;
- testar permissões por papel;
- testar importação CSV com casos reais e casos problemáticos;
- testar contratos de API quando endpoints DRF forem criados ou alterados;
- evitar regra de negócio relevante apenas em serializers, views ou JavaScript.

## 12. Organização sugerida de apps Django

A organização deve favorecer fronteiras claras de domínio e já parte de um **bootstrap Django manual mínimo materializado**.

### Estrutura atual consolidada

```text
config/
  settings/
    base.py
    dev.py
    test.py
  urls.py
  asgi.py
  wsgi.py
apps/
  core/       (infraestrutura comum: API, paginação, envelope de erro, OpenAPI)
  users/      (usuário customizado, matrícula, setores, papéis, policies)
  materials/  (grupos, subgrupos, materiais, busca, parser/importação SCPI)
  stock/      (estoque, saldo disponível, movimentações, saldo inicial)
manage.py
tests/
```

### Diretriz estrutural atual

- Os apps Django devem ficar sob a pasta `apps/`.
- A pasta `config/` permanece responsável por settings, URLs, ASGI/WSGI e bootstrap do projeto.
- O app `apps/core/` deve ser **técnico e transversal**, limitado a infraestrutura comum como API, paginação, envelope de erro e schema OpenAPI. Ele não deve conter regra de negócio de domínio.
- O app de usuários oficial é `apps/users/`. Não criar `accounts` ou outro app alternativo de usuários sem decisão registrada.

Apps ou módulos de domínio podem ser criados conforme o escopo avançar:

- `requisitions`: cabeçalho, itens e ciclo geral da requisição.
- `notifications`: notificações internas.
- `reports`: relatórios e exportações CSV.
- módulos adicionais só devem ser criados quando houver ganho real de fronteira de domínio, não por antecipação.
