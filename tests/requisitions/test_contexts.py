from decimal import Decimal

import pytest
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.requisitions.contexts import (
    ContextoAtendimento,
    ContextoAutorizacao,
    ContextoCancelamento,
    ContextoEnvio,
)
from apps.requisitions.models import ItemRequisicao, Requisicao, StatusRequisicao
from apps.stock.models import EstoqueMaterial
from apps.users.models import PapelChoices, Setor, User


@pytest.fixture
def setor_solicitante(db):
    chefe = User.objects.create(
        matricula_funcional="C001",
        nome_completo="Chefe Setor",
        papel=PapelChoices.CHEFE_SETOR,
        is_active=True,
    )
    setor = Setor.objects.create(nome="Setor A", chefe_responsavel=chefe)
    chefe.setor = setor
    chefe.save(update_fields=["setor"])
    return setor


@pytest.fixture
def setor_almoxarifado(db):
    chefe = User.objects.create(
        matricula_funcional="C002",
        nome_completo="Chefe Almox",
        papel=PapelChoices.CHEFE_ALMOXARIFADO,
        is_active=True,
    )
    setor = Setor.objects.create(nome="Almoxarifado", chefe_responsavel=chefe)
    chefe.setor = setor
    chefe.save(update_fields=["setor"])
    return setor


@pytest.fixture
def criador(db, setor_solicitante):
    return User.objects.create(
        matricula_funcional="S001",
        nome_completo="Solicitante",
        papel=PapelChoices.SOLICITANTE,
        setor=setor_solicitante,
        is_active=True,
    )


@pytest.fixture
def chefe_setor(db, setor_solicitante):
    return setor_solicitante.chefe_responsavel


@pytest.fixture
def almoxarife(db, setor_almoxarifado):
    u = User.objects.create(
        matricula_funcional="A001",
        nome_completo="Almoxarife",
        papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
        setor=setor_almoxarifado,
        is_active=True,
    )
    return u


@pytest.fixture
def material(db):
    grupo = GrupoMaterial.objects.create(codigo_grupo="01", nome="Grupo 01")
    subgrupo = SubgrupoMaterial.objects.create(grupo=grupo, codigo_subgrupo="01", nome="Sub 01")
    mat = Material.objects.create(
        subgrupo=subgrupo,
        codigo_completo="01.01.001",
        sequencial="001",
        nome="Material Teste",
        unidade_medida="UN",
        is_active=True,
    )
    EstoqueMaterial.objects.create(
        material=mat, saldo_fisico=Decimal("100"), saldo_reservado=Decimal("0")
    )
    return mat


def _criar_requisicao(criador, setor, status, numero_publico=None, **kwargs):
    return Requisicao.objects.create(
        criador=criador,
        beneficiario=criador,
        setor_beneficiario=setor,
        status=status,
        numero_publico=numero_publico,
        **kwargs,
    )


def _adicionar_item(requisicao, material, qtd_sol, qtd_aut=None):
    return ItemRequisicao.objects.create(
        requisicao=requisicao,
        material=material,
        unidade_medida=material.unidade_medida,
        quantidade_solicitada=qtd_sol,
        quantidade_autorizada=qtd_aut or Decimal("0"),
    )


class TestContextoEnvio:
    def test_abre_com_is_primeiro_envio_true_quando_sem_numero_publico(
        self, db, criador, setor_solicitante, material
    ):
        req = _criar_requisicao(
            criador, setor_solicitante, StatusRequisicao.RASCUNHO, numero_publico=None
        )
        _adicionar_item(req, material, Decimal("1"))

        with ContextoEnvio.abrir(req, criador) as ctx:
            assert ctx.is_primeiro_envio is True
            assert ctx.requisicao.pk == req.pk
            assert ctx.ator == criador

    def test_abre_com_is_primeiro_envio_false_quando_tem_numero_publico(
        self, db, criador, setor_solicitante, material
    ):
        req = _criar_requisicao(
            criador,
            setor_solicitante,
            StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000001",
            data_envio_autorizacao="2026-01-01T10:00:00Z",
        )
        _adicionar_item(req, material, Decimal("1"))

        with ContextoEnvio.abrir(req, criador) as ctx:
            assert ctx.is_primeiro_envio is False

    def test_rejeita_ator_fora_de_escopo_como_404(
        self, db, criador, setor_solicitante, almoxarife, material
    ):
        req = _criar_requisicao(criador, setor_solicitante, StatusRequisicao.RASCUNHO)
        _adicionar_item(req, material, Decimal("1"))

        with pytest.raises(NotFound):
            with ContextoEnvio.abrir(req, almoxarife):
                pass

    def test_rejeita_requisicao_inexistente(self, db, criador):
        req_fake = Requisicao(pk=999999)

        with pytest.raises(NotFound):
            with ContextoEnvio.abrir(req_fake, criador):
                pass


class TestContextoAutorizacao:
    def test_abre_para_chefe_setor_com_requisicao_correta(
        self, db, criador, chefe_setor, setor_solicitante, material
    ):
        req = _criar_requisicao(
            criador,
            setor_solicitante,
            StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000001",
            data_envio_autorizacao="2026-01-01T10:00:00Z",
        )
        _adicionar_item(req, material, Decimal("5"))

        with ContextoAutorizacao.abrir(req, chefe_setor) as ctx:
            assert ctx.requisicao.pk == req.pk
            assert ctx.ator == chefe_setor

    def test_rejeita_solicitante_sem_permissao(self, db, criador, setor_solicitante, material):
        req = _criar_requisicao(
            criador,
            setor_solicitante,
            StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000001",
            data_envio_autorizacao="2026-01-01T10:00:00Z",
        )
        _adicionar_item(req, material, Decimal("5"))

        with pytest.raises(PermissionDenied):
            with ContextoAutorizacao.abrir(req, criador):
                pass


class TestContextoCancelamento:
    def test_requer_liberacao_estoque_false_para_req_pre_autorizacao(
        self, db, criador, setor_solicitante
    ):
        req = _criar_requisicao(criador, setor_solicitante, StatusRequisicao.RASCUNHO)

        with ContextoCancelamento.abrir(req, criador) as ctx:
            assert ctx.requer_liberacao_estoque is False
            assert ctx.requisicao.pk == req.pk

    def test_requer_liberacao_estoque_true_para_req_autorizada(
        self, db, criador, chefe_setor, setor_solicitante, material
    ):
        req = _criar_requisicao(
            criador,
            setor_solicitante,
            StatusRequisicao.AUTORIZADA,
            numero_publico="REQ-2026-000001",
            data_envio_autorizacao="2026-01-01T10:00:00Z",
            data_autorizacao_ou_recusa="2026-01-01T11:00:00Z",
            chefe_autorizador=chefe_setor,
        )
        _adicionar_item(req, material, Decimal("5"), qtd_aut=Decimal("5"))

        with ContextoCancelamento.abrir(req, criador) as ctx:
            assert ctx.requer_liberacao_estoque is True

    def test_rejeita_ator_fora_de_escopo_rascunho_como_404(
        self, db, criador, setor_solicitante, almoxarife
    ):
        req = _criar_requisicao(criador, setor_solicitante, StatusRequisicao.RASCUNHO)

        with pytest.raises(NotFound):
            with ContextoCancelamento.abrir(req, almoxarife):
                pass

    def test_rejeita_chefe_setor_visivel_mas_sem_permissao_cancelamento_autorizada_como_403(
        self, db, criador, chefe_setor, setor_solicitante, material
    ):
        req = _criar_requisicao(
            criador,
            setor_solicitante,
            StatusRequisicao.AUTORIZADA,
            numero_publico="REQ-2026-000002",
            data_envio_autorizacao="2026-01-01T10:00:00Z",
            data_autorizacao_ou_recusa="2026-01-01T11:00:00Z",
            chefe_autorizador=chefe_setor,
        )
        _adicionar_item(req, material, Decimal("5"), qtd_aut=Decimal("5"))

        with pytest.raises(PermissionDenied):
            with ContextoCancelamento.abrir(req, chefe_setor):
                pass


class TestContextoAtendimento:
    def test_abre_para_almoxarife_com_req_autorizada(
        self, db, criador, chefe_setor, setor_solicitante, almoxarife, material
    ):
        req = _criar_requisicao(
            criador,
            setor_solicitante,
            StatusRequisicao.AUTORIZADA,
            numero_publico="REQ-2026-000001",
            data_envio_autorizacao="2026-01-01T10:00:00Z",
            data_autorizacao_ou_recusa="2026-01-01T11:00:00Z",
            chefe_autorizador=chefe_setor,
        )
        _adicionar_item(req, material, Decimal("5"), qtd_aut=Decimal("5"))

        with ContextoAtendimento.abrir(req, almoxarife) as ctx:
            assert ctx.requisicao.pk == req.pk
            assert ctx.ator == almoxarife

    def test_rejeita_solicitante_sem_permissao(
        self, db, criador, chefe_setor, setor_solicitante, material
    ):
        req = _criar_requisicao(
            criador,
            setor_solicitante,
            StatusRequisicao.AUTORIZADA,
            numero_publico="REQ-2026-000001",
            data_envio_autorizacao="2026-01-01T10:00:00Z",
            data_autorizacao_ou_recusa="2026-01-01T11:00:00Z",
            chefe_autorizador=chefe_setor,
        )
        _adicionar_item(req, material, Decimal("5"), qtd_aut=Decimal("5"))

        with pytest.raises(PermissionDenied):
            with ContextoAtendimento.abrir(req, criador):
                pass
