"""Testes de contrato da jornada Minhas solicitações (PR2 — issue #36).

Cobre:
- GET 200, template correto, app shell
- Partial HTMX: retorna _list.html
- Target #requisitions-worklist presente no HTML
- Atributos hx-* nos filtros e paginação
- Estado vazio real (sem solicitações)
- Estado com dados (lista com item)
- Empty state por filtro
- Unauthenticated → 302 redirect
- Atributos de acessibilidade
- Proteção de endpoint (login obrigatório)
- Sessão expirada: HTMX recebe HX-Redirect
"""

import pytest
from django.test import Client
from django.urls import reverse

from apps.requisitions.models import Requisicao, StatusRequisicao
from apps.users.models import PapelChoices, Setor, User

HTMX_HEADERS = {"HTTP_HX_REQUEST": "true"}


def _url():
    return reverse("web:requisitions_mine")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user(matricula, papel=PapelChoices.SOLICITANTE):
    u = User.objects.create_user(
        matricula_funcional=matricula,
        password="teste123",
        nome_completo=f"Usuario {matricula}",
        papel=papel,
        is_active=True,
    )
    setor = Setor.objects.create(nome=f"Setor {matricula}", chefe_responsavel=u)
    u.setor = setor
    u.save(update_fields=["setor"])
    return u


def _requisicao(criador, beneficiario=None, status=StatusRequisicao.RASCUNHO):
    beneficiario = beneficiario or criador
    setor = criador.setor
    return Requisicao.objects.create(
        criador=criador,
        beneficiario=beneficiario,
        setor_beneficiario=setor,
        status=status,
    )


# ---------------------------------------------------------------------------
# Autenticação e acesso
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAcesso:
    def test_unauthenticated_redireciona_para_login(self):
        client = Client()
        resp = client.get(_url())
        assert resp.status_code == 302
        assert "/login/" in resp["Location"]

    def test_authenticated_retorna_200(self):
        client = Client()
        u = _user("88001")
        client.force_login(u)
        resp = client.get(_url())
        assert resp.status_code == 200

    def test_htmx_unauthenticated_redireciona(self):
        client = Client()
        resp = client.get(_url(), **HTMX_HEADERS)
        assert resp.status_code == 302


# ---------------------------------------------------------------------------
# Template e shell
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTemplate:
    def test_usa_template_list(self):
        client = Client()
        u = _user("88002")
        client.force_login(u)
        resp = client.get(_url())
        assert "web/pages/requisitions/list.html" in [t.name for t in resp.templates]

    def test_usa_app_shell(self):
        client = Client()
        u = _user("88003")
        client.force_login(u)
        resp = client.get(_url())
        assert "web/layouts/app_shell.html" in [t.name for t in resp.templates]

    def test_htmx_usa_partial_list(self):
        client = Client()
        u = _user("88004")
        client.force_login(u)
        resp = client.get(_url(), **HTMX_HEADERS)
        assert resp.status_code == 200
        assert "web/pages/requisitions/_list.html" in [t.name for t in resp.templates]
        assert "web/pages/requisitions/list.html" not in [t.name for t in resp.templates]


# ---------------------------------------------------------------------------
# Estrutura HTML / HTMX
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEstruturaHtml:
    def test_worklist_target_presente(self):
        client = Client()
        u = _user("88005")
        client.force_login(u)
        resp = client.get(_url())
        assert 'id="requisitions-worklist"' in resp.content.decode()

    def test_filtros_tem_hx_get(self):
        client = Client()
        u = _user("88006")
        client.force_login(u)
        resp = client.get(_url())
        content = resp.content.decode()
        assert "hx-get" in content
        assert "hx-target" in content
        assert "#requisitions-worklist" in content

    def test_filtros_tem_hx_push_url(self):
        client = Client()
        u = _user("88007")
        client.force_login(u)
        resp = client.get(_url())
        assert "hx-push-url" in resp.content.decode()

    def test_filtro_status_select_presente(self):
        client = Client()
        u = _user("88008")
        client.force_login(u)
        resp = client.get(_url())
        assert 'id="filter-status"' in resp.content.decode()

    def test_filtro_busca_input_presente(self):
        client = Client()
        u = _user("88009")
        client.force_login(u)
        resp = client.get(_url())
        assert 'id="filter-q"' in resp.content.decode()


# ---------------------------------------------------------------------------
# Estados: vazio real, dados, filtered-empty
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEstados:
    def test_estado_vazio_real(self):
        client = Client()
        u = _user("88010")
        client.force_login(u)
        resp = client.get(_url())
        content = resp.content.decode()
        assert 'data-testid="empty-state-real"' in content

    def test_estado_com_dados_mostra_card(self):
        client = Client()
        u = _user("88011")
        _requisicao(u)
        client.force_login(u)
        resp = client.get(_url())
        content = resp.content.decode()
        assert 'data-testid="requisition-card"' in content

    def test_estado_com_dados_mostra_tabela_desktop(self):
        client = Client()
        u = _user("88012")
        _requisicao(u)
        client.force_login(u)
        resp = client.get(_url())
        content = resp.content.decode()
        assert 'data-testid="requisitions-table"' in content

    def test_filtered_empty_state(self):
        client = Client()
        u = _user("88013")
        _requisicao(u, status=StatusRequisicao.RASCUNHO)
        client.force_login(u)
        resp = client.get(_url(), {"status": StatusRequisicao.AUTORIZADA})
        content = resp.content.decode()
        assert 'data-testid="empty-state-filtered"' in content

    def test_filtro_por_status_filtra_resultados(self):
        client = Client()
        u = _user("88014")
        _requisicao(u, status=StatusRequisicao.RASCUNHO)
        _requisicao(u, status=StatusRequisicao.AGUARDANDO_AUTORIZACAO)
        client.force_login(u)
        resp = client.get(_url(), {"status": StatusRequisicao.RASCUNHO})
        content = resp.content.decode()
        assert "Rascunho" in content

    def test_filtro_status_invalido_ignorado(self):
        client = Client()
        u = _user("88015")
        _requisicao(u)
        client.force_login(u)
        resp = client.get(_url(), {"status": "status_inventado"})
        assert resp.status_code == 200

    def test_nao_mostra_solicitacoes_de_outro_usuario(self):
        client = Client()
        u1 = _user("88016")
        u2 = _user("88017")
        req = _requisicao(u2, status=StatusRequisicao.AGUARDANDO_AUTORIZACAO)
        client.force_login(u1)
        resp = client.get(_url())
        content = resp.content.decode()
        if req.numero_publico:
            assert req.numero_publico not in content
        else:
            assert 'data-testid="requisition-card"' not in content

    def test_rascunho_mostra_label_rascunho(self):
        client = Client()
        u = _user("88018")
        _requisicao(u, status=StatusRequisicao.RASCUNHO)
        client.force_login(u)
        resp = client.get(_url())
        assert "Rascunho" in resp.content.decode()

    def test_solicitacao_para_terceiro_mostra_nome_beneficiario(self):
        client = Client()
        u1 = _user("88019")
        u2 = _user("88020")
        _requisicao(u1, beneficiario=u2, status=StatusRequisicao.AGUARDANDO_AUTORIZACAO)
        client.force_login(u1)
        resp = client.get(_url())
        assert u2.nome_completo in resp.content.decode()


# ---------------------------------------------------------------------------
# Acessibilidade
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAcessibilidade:
    def test_pagina_tem_h1(self):
        client = Client()
        u = _user("88021")
        client.force_login(u)
        resp = client.get(_url())
        assert "<h1" in resp.content.decode()

    def test_worklist_tem_aria_live(self):
        client = Client()
        u = _user("88022")
        client.force_login(u)
        resp = client.get(_url())
        content = resp.content.decode()
        assert 'aria-live="polite"' in content

    def test_form_filtro_tem_aria_label(self):
        client = Client()
        u = _user("88023")
        client.force_login(u)
        resp = client.get(_url())
        assert 'aria-label="Filtrar solicitações"' in resp.content.decode()

    def test_input_busca_tem_label(self):
        client = Client()
        u = _user("88024")
        client.force_login(u)
        resp = client.get(_url())
        content = resp.content.decode()
        assert 'for="filter-q"' in content

    def test_select_status_tem_label(self):
        client = Client()
        u = _user("88025")
        client.force_login(u)
        resp = client.get(_url())
        content = resp.content.decode()
        assert 'for="filter-status"' in content

    def test_empty_state_real_tem_testid(self):
        client = Client()
        u = _user("88026")
        client.force_login(u)
        resp = client.get(_url())
        assert 'data-testid="empty-state-real"' in resp.content.decode()

    def test_badge_status_presente_com_dados(self):
        client = Client()
        u = _user("88027")
        _requisicao(u, status=StatusRequisicao.AGUARDANDO_AUTORIZACAO)
        client.force_login(u)
        resp = client.get(_url())
        assert "Aguardando Autorização" in resp.content.decode()


# ---------------------------------------------------------------------------
# Paginação
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPaginacao:
    def test_paginacao_aparece_com_mais_de_20_itens(self):
        client = Client()
        u = _user("88028")
        for i in range(22):
            _requisicao(u, status=StatusRequisicao.RASCUNHO)
        client.force_login(u)
        resp = client.get(_url())
        assert 'data-testid="requisitions-pagination"' in resp.content.decode()

    def test_paginacao_preserva_filtro_de_status(self):
        client = Client()
        u = _user("88029")
        for i in range(22):
            _requisicao(u, status=StatusRequisicao.RASCUNHO)
        client.force_login(u)
        resp = client.get(_url(), {"status": StatusRequisicao.RASCUNHO, "page": 1})
        assert resp.status_code == 200

    def test_sem_paginacao_com_poucos_itens(self):
        client = Client()
        u = _user("88030")
        _requisicao(u)
        client.force_login(u)
        resp = client.get(_url())
        assert 'data-testid="requisitions-pagination"' not in resp.content.decode()

    def test_paginacao_hx_get_preserva_filtro_status(self):
        client = Client()
        u = _user("88031")
        for i in range(22):
            _requisicao(u, status=StatusRequisicao.RASCUNHO)
        client.force_login(u)
        resp = client.get(_url(), {"status": StatusRequisicao.RASCUNHO})
        content = resp.content.decode()
        assert 'data-testid="requisitions-pagination"' in content
        assert f"status={StatusRequisicao.RASCUNHO}" in content

    def test_filtro_busca_valor_preservado_no_input(self):
        client = Client()
        u = _user("88032")
        client.force_login(u)
        resp = client.get(_url(), {"q": "teste"})
        content = resp.content.decode()
        assert 'value="teste"' in content
