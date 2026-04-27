"""
Testes para PapelChoices, campo papel e funções de policy em apps/users.

Cobre os invariantes:
  PER-01 — Solicitante cria apenas para si.
  PER-02 — Auxiliar de setor atua apenas no próprio setor.
  PER-03 — Chefe autoriza só setor do beneficiário.
  PER-04 — Almoxarifado cria em nome de qualquer funcionário.
  PER-05 — Chefe de Almoxarifado herda auxiliar de Almoxarifado.
  PER-06 — Superusuário é suporte/admin, não operador cotidiano de estoque.
"""

import pytest

from apps.users.models import PapelChoices, Setor, User
from apps.users.policies import (
    pode_autorizar_setor,
    pode_criar_requisicao_para,
    pode_operar_estoque,
    pode_operar_estoque_chefia,
    pode_ver_fila_atendimento,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _criar_user(matricula, papel=PapelChoices.SOLICITANTE, setor=None, **kwargs):
    return User.objects.create_user(
        matricula_funcional=matricula,
        password="testpass123",
        nome_completo=f"Usuário {matricula}",
        papel=papel,
        setor=setor,
        **kwargs,
    )


def _criar_setor(nome, chefe):
    return Setor.objects.create(nome=nome, chefe_responsavel=chefe)


# ---------------------------------------------------------------------------
# 1. Default do campo papel
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPapelDefault:
    def test_usuario_novo_tem_papel_solicitante_por_default(self):
        """USR-04 / PER-01: todo usuário ativo é solicitante por padrão."""
        user = User.objects.create_user(
            matricula_funcional="00001",
            password="testpass123",
            nome_completo="Usuário Padrão",
        )
        assert user.papel == PapelChoices.SOLICITANTE


# ---------------------------------------------------------------------------
# 2. pode_criar_requisicao_para
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPodeCriarRequisicaoPara:
    """Testa PER-01, PER-02 e PER-04."""

    def test_per01_solicitante_pode_criar_para_si(self):
        """PER-01 — caminho feliz: solicitante cria para si mesmo."""
        user = _criar_user("10001", PapelChoices.SOLICITANTE)
        assert pode_criar_requisicao_para(user, user) is True

    def test_per01_solicitante_nao_pode_criar_para_terceiro(self):
        """PER-01 — negado: solicitante não pode criar para outro usuário."""
        user = _criar_user("10002", PapelChoices.SOLICITANTE)
        outro = _criar_user("10003", PapelChoices.SOLICITANTE)
        assert pode_criar_requisicao_para(user, outro) is False

    def test_per02_auxiliar_setor_pode_criar_para_mesmo_setor(self):
        """PER-02 — caminho feliz: auxiliar cria para funcionário do próprio setor."""
        chefe = _criar_user("20001", PapelChoices.CHEFE_SETOR)
        setor = _criar_setor("TI", chefe)

        auxiliar = _criar_user("20002", PapelChoices.AUXILIAR_SETOR, setor=setor)
        beneficiario = _criar_user("20003", PapelChoices.SOLICITANTE, setor=setor)

        assert pode_criar_requisicao_para(auxiliar, beneficiario) is True

    def test_per02_auxiliar_setor_nao_pode_criar_para_outro_setor(self):
        """PER-02 — negado: auxiliar não pode criar para funcionário de outro setor."""
        chefe_a = _criar_user("20004", PapelChoices.CHEFE_SETOR)
        chefe_b = _criar_user("20005", PapelChoices.CHEFE_SETOR)
        setor_a = _criar_setor("TI", chefe_a)
        setor_b = _criar_setor("RH", chefe_b)

        auxiliar = _criar_user("20006", PapelChoices.AUXILIAR_SETOR, setor=setor_a)
        beneficiario = _criar_user("20007", PapelChoices.SOLICITANTE, setor=setor_b)

        assert pode_criar_requisicao_para(auxiliar, beneficiario) is False

    def test_per03_chefe_setor_pode_criar_para_setor_sob_responsabilidade(self):
        """PER-03 — chefe usa o setor sob responsabilidade, não a lotação atual."""
        chefe = _criar_user("20008", PapelChoices.CHEFE_SETOR)
        setor = _criar_setor("Financeiro", chefe)
        beneficiario = _criar_user("20009", PapelChoices.SOLICITANTE, setor=setor)

        assert pode_criar_requisicao_para(chefe, beneficiario) is True

    def test_per03_chefe_setor_sem_responsabilidade_nao_herda_escopo_por_lotacao(self):
        """PER-03 — marcar papel de chefe sem setor_responsavel não concede escopo."""
        chefe_responsavel = _criar_user("20010", PapelChoices.CHEFE_SETOR)
        setor = _criar_setor("Compras", chefe_responsavel)
        pseudo_chefe = _criar_user("20011", PapelChoices.CHEFE_SETOR, setor=setor)
        beneficiario = _criar_user("20012", PapelChoices.SOLICITANTE, setor=setor)

        assert pode_criar_requisicao_para(pseudo_chefe, beneficiario) is False

    def test_per04_auxiliar_almoxarifado_pode_criar_para_qualquer_funcionario(self):
        """PER-04 — caminho feliz: auxiliar de Almoxarifado cria para qualquer setor."""
        chefe_alm = _criar_user("30001", PapelChoices.CHEFE_ALMOXARIFADO)
        setor_alm = _criar_setor("Almoxarifado", chefe_alm)

        chefe_outro = _criar_user("30002", PapelChoices.CHEFE_SETOR)
        setor_outro = _criar_setor("Obras", chefe_outro)

        auxiliar = _criar_user("30003", PapelChoices.AUXILIAR_ALMOXARIFADO, setor=setor_alm)
        beneficiario = _criar_user("30004", PapelChoices.SOLICITANTE, setor=setor_outro)

        assert pode_criar_requisicao_para(auxiliar, beneficiario) is True

    def test_per05_chefe_almoxarifado_pode_criar_para_qualquer_funcionario(self):
        """PER-05 — Chefe de Almoxarifado herda capacidade de criar para qualquer setor."""
        chefe_alm = _criar_user("40001", PapelChoices.CHEFE_ALMOXARIFADO)
        _criar_setor("Almoxarifado", chefe_alm)

        chefe_outro = _criar_user("40002", PapelChoices.CHEFE_SETOR)
        setor_outro = _criar_setor("Manutenção", chefe_outro)

        beneficiario = _criar_user("40003", PapelChoices.SOLICITANTE, setor=setor_outro)

        assert pode_criar_requisicao_para(chefe_alm, beneficiario) is True

    def test_per06_superusuario_nao_pode_criar_requisicao_para_si(self):
        """PER-06 — Superusuário não opera como usuário cotidiano (nem para si)."""
        superuser = User.objects.create_superuser(
            matricula_funcional="99001",
            password="testpass123",
            nome_completo="Super Admin",
        )
        assert pode_criar_requisicao_para(superuser, superuser) is False

    def test_usuario_inativo_nao_pode_criar_requisicao(self):
        """USR-03 — Usuário inativo não opera."""
        user = _criar_user("50001", PapelChoices.SOLICITANTE, is_active=False)
        assert pode_criar_requisicao_para(user, user) is False


# ---------------------------------------------------------------------------
# 3. pode_autorizar_setor
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPodeAutorizarSetor:
    """Testa PER-03 e PER-06."""

    def test_per03_chefe_setor_pode_autorizar_proprio_setor(self):
        """PER-03 — caminho feliz: chefe autoriza requisição do próprio setor."""
        chefe = _criar_user("60001", PapelChoices.CHEFE_SETOR)
        setor = _criar_setor("Contabilidade", chefe)
        chefe.setor = setor
        chefe.save(update_fields=["setor"])

        assert pode_autorizar_setor(chefe, setor) is True

    def test_per03_chefe_setor_nao_pode_autorizar_outro_setor(self):
        """PER-03 — negado: chefe não pode autorizar setor do qual não é responsável."""
        chefe_a = _criar_user("60002", PapelChoices.CHEFE_SETOR)
        chefe_b = _criar_user("60003", PapelChoices.CHEFE_SETOR)
        _criar_setor("Contabilidade", chefe_a)
        setor_b = _criar_setor("Jurídico", chefe_b)

        assert pode_autorizar_setor(chefe_a, setor_b) is False

    def test_per05_chefe_almoxarifado_nao_pode_autorizar_outro_setor(self):
        """PER-05 — Chefe de Almoxarifado autoriza APENAS seu setor Almoxarifado."""
        chefe_alm = _criar_user("60004", PapelChoices.CHEFE_ALMOXARIFADO)
        setor_alm = _criar_setor("Almoxarifado", chefe_alm)
        chefe_alm.setor = setor_alm
        chefe_alm.save(update_fields=["setor"])

        chefe_outro = _criar_user("60005", PapelChoices.CHEFE_SETOR)
        setor_outro = _criar_setor("Obras", chefe_outro)

        assert pode_autorizar_setor(chefe_alm, setor_outro) is False

    def test_per06_superusuario_nao_pode_autorizar_setor(self):
        """PER-06 — Superusuário não autoriza requisições operacionais."""
        superuser = User.objects.create_superuser(
            matricula_funcional="99002",
            password="testpass123",
            nome_completo="Super Admin 2",
        )
        chefe = _criar_user("60006", PapelChoices.CHEFE_SETOR)
        setor = _criar_setor("Planejamento", chefe)

        assert pode_autorizar_setor(superuser, setor) is False


# ---------------------------------------------------------------------------
# 4. pode_ver_fila_atendimento e pode_operar_estoque
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFilaAtendimentoEEstoque:
    """Testa PER-04, PER-05 e PER-06 nas funções operacionais."""

    def test_auxiliar_almoxarifado_pode_ver_fila_atendimento(self):
        """PER-04 — Auxiliar de Almoxarifado vê fila de atendimento."""
        user = _criar_user("70001", PapelChoices.AUXILIAR_ALMOXARIFADO)
        assert pode_ver_fila_atendimento(user) is True

    def test_solicitante_nao_pode_ver_fila_atendimento(self):
        """Solicitante não tem acesso à fila de atendimento."""
        user = _criar_user("70002", PapelChoices.SOLICITANTE)
        assert pode_ver_fila_atendimento(user) is False

    def test_per05_chefe_almoxarifado_pode_operar_estoque(self):
        """PER-05 — Chefe de Almoxarifado herda operação de estoque."""
        user = _criar_user("70003", PapelChoices.CHEFE_ALMOXARIFADO)
        assert pode_operar_estoque(user) is True

    def test_auxiliar_almoxarifado_nao_pode_operar_estoque_chefia(self):
        """PER-05 — auxiliar não recebe saída excepcional nem estorno."""
        user = _criar_user("70004", PapelChoices.AUXILIAR_ALMOXARIFADO)
        assert pode_operar_estoque_chefia(user) is False

    def test_per05_chefe_almoxarifado_pode_operar_estoque_chefia(self):
        """PER-05 — chefe de Almoxarifado pode executar ações exclusivas de chefia."""
        user = _criar_user("70005", PapelChoices.CHEFE_ALMOXARIFADO)
        assert pode_operar_estoque_chefia(user) is True

    def test_per06_superusuario_nao_pode_operar_estoque(self):
        """PER-06 — Superusuário bloqueado de operações de estoque."""
        superuser = User.objects.create_superuser(
            matricula_funcional="99003",
            password="testpass123",
            nome_completo="Super Admin 3",
        )
        assert pode_operar_estoque(superuser) is False
        assert pode_operar_estoque_chefia(superuser) is False
