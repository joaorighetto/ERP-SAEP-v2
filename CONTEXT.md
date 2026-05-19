# WMS-SAEP

Contexto do fluxo operacional do almoxarifado do SAEP para requisição, autorização e atendimento de materiais. Este documento fixa a linguagem de domínio usada para papéis, filas e responsabilidades operacionais.

## Language

**Solicitante**:
Usuário ativo que cria requisição para si e acompanha suas próprias requisições.
_Avoid_: requisitante, requerente

**Auxiliar de setor**:
Usuário que pode criar requisições em nome de funcionários do próprio setor, sem poder autorizar requisições.
_Avoid_: autorizador auxiliar, aprovador do setor

**Chefe de setor**:
Usuário responsável por autorizar ou recusar requisições do setor sob sua responsabilidade.
_Avoid_: gestor genérico, aprovador global

**Auxiliar de Almoxarifado**:
Usuário operacional do Almoxarifado que atende requisições autorizadas e registra a retirada de materiais.
_Avoid_: autorizador do Almoxarifado

**Chefe de Almoxarifado**:
Usuário que opera o fluxo do Almoxarifado e também autoriza apenas requisições cujo setor do beneficiário é o próprio Almoxarifado.
_Avoid_: autorizador de qualquer setor

**Papel operacional principal**:
Papel único atribuído ao usuário para definir seu escopo operacional no piloto.
_Avoid_: combinação livre de múltiplos papéis ativos

**Fila de autorizações**:
Lista de requisições em `aguardando autorização` visível apenas para quem pode autorizar no seu escopo.
_Avoid_: fila geral do setor, caixa de entrada de qualquer usuário

**Fila de atendimento**:
Lista de requisições autorizadas disponíveis para operação do Almoxarifado.
_Avoid_: fila de autorização, lista do solicitante

**Minhas requisições**:
Lista de trabalho do usuário para acompanhar requisições próprias como criador ou beneficiário.
_Avoid_: fila de autorização, fila de atendimento

**Descartar rascunho**:
Exclusão de um rascunho que nunca foi enviado para autorização e ainda não virou requisição formal.
_Avoid_: cancelar rascunho, apagar requisição formal

**Cancelar requisição**:
Encerramento lógico de uma requisição formalizada, preservando seu histórico.
_Avoid_: descartar, apagar do sistema

## Relationships

- Um **Solicitante** acompanha suas **Minhas requisições**
- Um **Auxiliar de setor** apoia o próprio setor criando requisições, mas não entra na **Fila de autorizações**
- Um **Chefe de setor** trabalha na **Fila de autorizações** do setor sob sua responsabilidade
- Um **Auxiliar de Almoxarifado** trabalha na **Fila de atendimento**
- Um **Chefe de Almoxarifado** trabalha na **Fila de atendimento** e só autoriza requisições do setor Almoxarifado
- Cada usuário opera o piloto com um único **Papel operacional principal**
- **Descartar rascunho** só existe antes da formalização da requisição
- **Cancelar requisição** só se aplica a uma requisição já formalizada

## Example dialogue

> **Dev:** "O **Auxiliar de setor** entra na **Fila de autorizações** quando a requisição do setor é enviada?"
> **Especialista:** "Não. O **Auxiliar de setor** pode preparar a requisição para o setor, mas quem decide a autorização é o **Chefe de setor**."
>
> **Dev:** "Para o usuário, **Descartar rascunho** e **Cancelar requisição** são a mesma coisa?"
> **Especialista:** "Não. **Descartar rascunho** apaga algo que ainda não virou requisição formal. **Cancelar requisição** encerra uma requisição formal e mantém o histórico."
>
> **Dev:** "O frontend deve assumir que o usuário pode acumular vários papéis operacionais ao mesmo tempo?"
> **Especialista:** "Não no piloto atual. Cada usuário opera com um único **Papel operacional principal**."

## Flagged ambiguities

- "auxiliar de setor" foi usado como se também fosse autorizador — resolvido: ele apoia a criação de requisições do próprio setor, mas não autoriza
- "descartar" e "cancelar" podem soar iguais na UI — resolvido: **Descartar rascunho** apaga o rascunho nunca formalizado; **Cancelar requisição** encerra uma requisição formal preservando histórico
- "papéis múltiplos simultâneos" foi assumido no frontend — resolvido: o piloto atual usa um único **Papel operacional principal** por usuário
