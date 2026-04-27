"""
Funções de autorização contextual para o app users.

Centraliza todas as regras de permissão por papel e escopo, seguindo
a matriz-permissoes.md. Views e services devem invocar estas funções
para garantir que a mesma lógica seja aplicada em ambas as camadas
(invariante PER-08).
"""

from .models import PapelChoices


def _user_ativo_nao_superuser(user) -> bool:
    return user.is_active and not user.is_superuser


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
    if not _user_ativo_nao_superuser(criador):
        return False

    papel = criador.papel

    if papel in (PapelChoices.AUXILIAR_ALMOXARIFADO, PapelChoices.CHEFE_ALMOXARIFADO):
        return True

    if papel == PapelChoices.SOLICITANTE:
        return criador.pk == beneficiario.pk

    if papel == PapelChoices.AUXILIAR_SETOR:
        if criador.setor_id is None or beneficiario.setor_id is None:
            return False
        setor_escopo_id = criador.setor_id
        return setor_escopo_id == beneficiario.setor_id

    if papel == PapelChoices.CHEFE_SETOR:
        setor_responsavel = getattr(criador, "setor_responsavel", None)
        if setor_responsavel is None or beneficiario.setor_id is None:
            return False
        return setor_responsavel.pk == beneficiario.setor_id

    return False


def pode_autorizar_setor(autorizador, setor) -> bool:
    """
    Verifica se `autorizador` pode autorizar requisições do `setor` informado.

    Regras (matriz-permissoes.md, seção 4):
    - Chefe de setor: apenas o setor pelo qual é responsável (setor_responsavel).
    - Chefe de Almoxarifado: autoriza APENAS requisições do setor Almoxarifado.
      Nota: o setor Almoxarifado é aquele ao qual o chefe pertence (setor_id).
    - Demais papéis e superusuário: nunca.
    - Usuário inativo: nunca (invariante USR-03).
    """
    if not _user_ativo_nao_superuser(autorizador):
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
    if not _user_ativo_nao_superuser(user):
        return False

    return user.papel in (
        PapelChoices.AUXILIAR_ALMOXARIFADO,
        PapelChoices.CHEFE_ALMOXARIFADO,
    )


def pode_operar_estoque(user) -> bool:
    """
    Verifica se `user` pode executar operações operacionais comuns de estoque
    (atendimento, devolução e ações correlatas de fluxo normal).

    Regras (matriz-permissoes.md, seção 4):
    - Auxiliar de Almoxarifado: sim (atendimento e devolução).
    - Chefe de Almoxarifado: sim (herda as operações comuns do auxiliar).
    - Superusuário: nunca (invariante PER-06).
    - Demais papéis: não.
    - Usuário inativo: nunca (invariante USR-03).
    """
    if not _user_ativo_nao_superuser(user):
        return False

    return user.papel in (
        PapelChoices.AUXILIAR_ALMOXARIFADO,
        PapelChoices.CHEFE_ALMOXARIFADO,
    )


def pode_operar_estoque_chefia(user) -> bool:
    """
    Verifica se `user` pode executar operações exclusivas da chefia
    do Almoxarifado (saída excepcional, estornos e equivalentes).

    Regras (matriz-permissoes.md, seção 4):
    - Chefe de Almoxarifado: sim.
    - Auxiliar de Almoxarifado: não.
    - Superusuário: nunca (invariante PER-06).
    - Demais papéis: não.
    - Usuário inativo: nunca (invariante USR-03).
    """
    if not _user_ativo_nao_superuser(user):
        return False

    return user.papel == PapelChoices.CHEFE_ALMOXARIFADO
