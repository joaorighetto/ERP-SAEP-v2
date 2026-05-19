# AGENTS.md

Este arquivo é o **traffic marshal** da documentação do WMS-SAEP. Ele não é a documentação de domínio em si; ele indica a rota correta para agentes encontrarem a fonte mais adequada sem ler documentos demais nem decidir com base em fonte incompleta.

## Rota padrão

Antes de implementar, revisar ou propor mudança:

1. Comece por `design-acesso-rapido/`.
2. Consulte `design-acesso-ocasional/` apenas quando a síntese rápida não resolver a dúvida, houver ambiguidade ou a tarefa depender de detalhe de domínio.
3. Consulte `backlog/` para entender fase, escopo, dependências e critérios de entrega.
4. Consulte `code-review-guidelines.md` quando a tarefa envolver revisão de código, invariantes arquiteturais, auditoria, transações, side effects ou padrões que o reviewer deve respeitar.

Em caso de conflito entre síntese rápida e documentação completa, prevalece `design-acesso-ocasional/`, salvo decisão posterior registrada. Mudanças de regra de negócio devem atualizar a documentação rápida e a documentação completa quando ambas forem afetadas.

## Rotas por necessidade

| Necessidade | Primeira parada | Quando aprofundar |
|---|---|---|
| Stack, arquitetura, decisões técnicas | `design-acesso-rapido/stack.md` | Consultar backlog ou documentação completa se a decisão afetar escopo de app, fronteira de domínio ou CI. |
| Arquitetura do frontend do piloto | `design-acesso-rapido/frontend-arquitetura-piloto.md` | Consultar o ADR em `adr/0009-frontend-piloto-django-htmx.md` quando a dúvida for sobre a decisão macro, trade-offs ou limites do reset. |
| Infraestrutura do frontend server-rendered | `design-acesso-rapido/frontend-arquitetura-piloto.md` | Usar quando a tarefa tocar templates, partials HTMX, assets Tailwind/Alpine ou novos comandos operacionais do frontend. |
| Contratos DRF, erros, paginação, OpenAPI | `design-acesso-rapido/api-contracts.md` | Consultar documentos de domínio quando o endpoint expõe regra crítica. |
| Invariantes de domínio | `design-acesso-rapido/matriz-invariantes.md` | Consultar `design-acesso-ocasional/modelo-dominio-regras.md`, `processos-almoxarifado.md` e `criterios-aceite.md` para detalhe. |
| Permissões, papéis e escopos | `design-acesso-rapido/matriz-permissoes.md` | Consultar `design-acesso-ocasional/modelo-dominio-regras.md` e `criterios-aceite.md` quando houver regra contextual por setor, objeto ou estado. |
| Estados e transições de requisição | `design-acesso-rapido/estado-transicoes-requisicao.md` | Consultar `design-acesso-ocasional/processos-almoxarifado.md` para fluxos alternativos e exceções. |
| Modelo de domínio e regras de negócio completas | `design-acesso-ocasional/modelo-dominio-regras.md` | Usar como fonte de verdade quando a síntese for insuficiente. |
| Fluxos do Almoxarifado | `design-acesso-ocasional/processos-almoxarifado.md` | Usar para criação, autorização, atendimento, cancelamento, devolução, saída excepcional e estorno. |
| Critérios de aceite | `design-acesso-ocasional/criterios-aceite.md` | Usar para definir testes mínimos e validar comportamento esperado. |
| Importação SCPI CSV | `design-acesso-ocasional/importacao-scpi-csv.md` | Usar para normalização, prévia, regra tudo ou nada, `QUAN3`, ausentes e divergência crítica. |
| Planejamento do piloto | `backlog/backlog-tecnico-piloto.md` | Usar para saber o que entra no piloto inicial e o que está fora. |
| Gate do frontend do piloto | `backlog/backlog-tecnico-piloto.md` | Usar para confirmar o contrato mínimo antes de abrir a frente server-rendered. |
| Planejamento do MVP | `backlog/backlog-tecnico-mvp.md` | Usar para rotinas complementares, relatórios, devoluções, saídas excepcionais, estornos e gestão. |
| Revisão automatizada e guardrails | `code-review-guidelines.md` | Usar antes de review, PR ou mudança que toque invariantes críticos. |

## Diretórios

- `design-acesso-rapido/`: sínteses operacionais. Deve ser a primeira fonte consultada por agentes.
- `design-acesso-ocasional/`: documentação completa. Deve ser consultada sob demanda, não como leitura padrão integral.
- `adr/`: decisões arquiteturais difíceis de reverter. Usar quando a dúvida for “por que foi decidido assim?”.
- `backlog/`: escopo, fases, dependências e entregáveis planejados.
- `code-review-guidelines.md`: invariantes arquiteturais e orientação para revisão.

## Regras de navegação

- Não leia todos os documentos por padrão; escolha a rota pelo tipo de dúvida.
- Não use backlog como fonte para contrariar regra de domínio já documentada.
- Não inicie features do frontend do piloto sem confirmar antes o contrato ativo no backlog e no guia operacional do frontend.
- Não ressuscite a fundação SPA removida sem nova decisão explícita.
- Não use síntese rápida para sobrescrever regra mais detalhada em `design-acesso-ocasional/`.
- Não aceite mudança de contrato HTTP sem atualizar `design-acesso-rapido/api-contracts.md`, testes e OpenAPI quando aplicável.
- Não aceite mudança de permissão sem revisar `design-acesso-rapido/matriz-permissoes.md`.
- Não aceite mudança de invariante sem revisar `design-acesso-rapido/matriz-invariantes.md`.
- Ao alterar regra de negócio, atualize a síntese rápida correspondente e a documentação completa afetada.

## Ordem de decisão em conflito

1. Decisão posterior explicitamente registrada.
2. Documentação completa em `design-acesso-ocasional/`.
3. Critérios de aceite em `design-acesso-ocasional/criterios-aceite.md`, quando a dúvida for comportamento verificável.
4. Matrizes e sínteses em `design-acesso-rapido/`.
5. Backlog, para escopo, fase, entregáveis e gates de implementação.

Se o conflito afetar domínio, permissão, estoque, requisição, importação SCPI, contrato DRF ou auditoria, registre a decisão no PR e atualize os documentos afetados.
