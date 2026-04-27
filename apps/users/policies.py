"""
Funções de autorização contextual para o app users.

Centraliza todas as regras de permissão por papel e escopo, seguindo
a matriz-permissoes.md. Views e services devem invocar estas funções
para garantir que a mesma lógica seja aplicada em ambas as camadas
(invariante PER-08).
"""

from .models import PapelChoices


def pode_criar_requisicao_para(criador, beneficiario) -> bool:
    """
    Verifica se `criador` pode criar uma requisição em nome de `beneficiario`.

    Regras (matriz-permissoes.md, seção 4):
    - Solicitante: apenas para si mesmo.
    - Auxiliar de setor: apenas para funcionários do próprio setor.
    - Chefe de setor: apenas para funcionários do próprio setor.
    - Auxiliar de Almoxarifado: qualquer funcionário.
    - Chefe de Almoxarifado: qualquer funcionário.
    - Superusuário: nunca (suporte/admin, não operador cotidiano).
    - Usuário inativo: nunca (invariante USR-03).
    """
    if not criador.is_active:
        return False

    if criador.is_superuser:
        return False

    papel = criador.papel

    if papel in (PapelChoices.AUXILIAR_ALMOXARIFADO, PapelChoices.CHEFE_ALMOXARIFADO):
        return True

    if papel == PapelChoices.SOLICITANTE:
        return criador.pk == beneficiario.pk

    if papel in (PapelChoices.AUXILIAR_SETOR, PapelChoices.CHEFE_SETOR):
        if criador.setor_id is None or beneficiario.setor_id is None:
            return False
        return criador.setor_id == beneficiario.setor_id

    return False


def pode_autorizar_setor(autorizador, setor) -> bool:
    """
    Verifica se `autorizador` pode autorizar requisições do `setor` informado.

    Regras (matriz-permissoes.md, seção 4):
    - Chefe de setor: apenas o setor pelo qual é responsável (setor_responsavel).
    - Chefe de Almoxarifado: apenas o setor Almoxarifado (o setor ao qual pertence).
    - Demais papéis e superusuário: nunca.
    - Usuário inativo: nunca (invariante USR-03).
    """
    if not autorizador.is_active:
        return False

    if autorizador.is_superuser:
        return False

    papel = autorizador.papel

    if papel == PapelChoices.CHEFE_SETOR:
        setor_responsavel = getattr(autorizador, "setor_responsavel", None)
        if setor_responsavel is None:
            return False
        return setor_responsavel.pk == setor.pk

    if papel == PapelChoices.CHEFE_ALMOXARIFADO:
        if autorizador.setor_id is None:
            return False
        return autorizador.setor_id == setor.pk

    return False


def pode_ver_fila_atendimento(user) -> bool:
    """
    Verifica se `user` pode acessar a fila de atendimento do Almoxarifado.

    Regras (matriz-permissoes.md, seção 4):
    - Auxiliar de Almoxarifado: sim.
    - Chefe de Almoxarifado: sim.
    - Superusuário: apenas suporte/admin — não acessa fila operacional.
    - Demais papéis: não.
    - Usuário inativo: nunca (invariante USR-03).
    """
    if not user.is_active:
        return False

    if user.is_superuser:
        return False

    return user.papel in (
        PapelChoices.AUXILIAR_ALMOXARIFADO,
        PapelChoices.CHEFE_ALMOXARIFADO,
    )


def pode_operar_estoque(user) -> bool:
    """
    Verifica se `user` pode executar operações formais de estoque
    (atendimento, devolução, saída excepcional, estorno).

    Regras (matriz-permissoes.md, seção 4):
    - Auxiliar de Almoxarifado: sim (atendimento e devolução).
    - Chefe de Almoxarifado: sim (herda auxiliar; adicionalmente saída excepcional e estorno).
    - Superusuário: nunca (invariante PER-06).
    - Demais papéis: não.
    - Usuário inativo: nunca (invariante USR-03).
    """
    if not user.is_active:
        return False

    if user.is_superuser:
        return False

    return user.papel in (
        PapelChoices.AUXILIAR_ALMOXARIFADO,
        PapelChoices.CHEFE_ALMOXARIFADO,
    )
