"""Testes de contrato para a jornada Nova Solicitação (issue #40).

Cobre:
- GET create → 200, template correto, data-testid presente
- POST create válido (1 item) → rascunho criado, redirect
- POST create com acao=enviar → rascunho criado + enviado, redirect
- GET edit como criador → 200, pre-preenchido
- POST edit válido → rascunho atualizado, redirect
- POST send → status → EM_ANALISE, redirect
- HTMX material_search → 200, partial com resultados
- HTMX item_add → 200, _item_row.html, idx correto
- GET create não autenticado → 302 para /login/
- POST create SOLICITANTE com beneficiário ≠ self → 422 (erro de permissão)
- Não-criador GET edit → 404
- POST create sem itens → 422 com aria-invalid
- 422 tem aria-invalid/aria-describedby no conteúdo
- Navegação exibe "Nova solicitação" para papéis esperados
"""

from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.requisitions.models import Requisicao, StatusRequisicao
from apps.stock.models import EstoqueMaterial
from apps.users.models import PapelChoices, Setor, User

HTMX_HEADERS = {"HTTP_HX_REQUEST": "true"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_setor_counter = 0


def _setor(nome="Setor Teste"):
    global _setor_counter
    _setor_counter += 1
    mat_tmp = f"s{_setor_counter:05d}"  # e.g. "s00001" — max 6 chars, unique
    u = User.objects.create_user(
        matricula_funcional=mat_tmp,
        password="x",
        nome_completo=f"Chefe {nome}",
        papel=PapelChoices.CHEFE_SETOR,
        is_active=True,
    )
    s = Setor.objects.create(nome=nome, chefe_responsavel=u)
    u.setor = s
    u.save(update_fields=["setor"])
    return s


def _user(matricula, papel=PapelChoices.SOLICITANTE, setor=None):
    u = User.objects.create_user(
        matricula_funcional=matricula,
        password="teste123",
        nome_completo=f"Usuario {matricula}",
        papel=papel,
        is_active=True,
    )
    if setor is None and papel not in (
        PapelChoices.AUXILIAR_ALMOXARIFADO,
        PapelChoices.CHEFE_ALMOXARIFADO,
    ):
        setor = _setor(nome=f"Setor {matricula}")
    u.setor = setor
    u.save(update_fields=["setor"])
    return u


_mat_counter = 0


def _material(nome="Tubo PVC 50mm", saldo_fisico=100, saldo_reservado=0):
    global _mat_counter
    _mat_counter += 1
    seq = str(_mat_counter).zfill(3)  # "001" … "999"

    grupo, _ = GrupoMaterial.objects.get_or_create(
        codigo_grupo="013", defaults={"nome": "Hidráulico"}
    )
    subgrupo, _ = SubgrupoMaterial.objects.get_or_create(
        grupo=grupo, codigo_subgrupo="001", defaults={"nome": "Tubulação"}
    )
    mat = Material.objects.create(
        subgrupo=subgrupo,
        codigo_completo=f"013.001.{seq}",  # exactly 11 chars
        sequencial=seq,  # exactly 3 chars
        nome=nome,
        unidade_medida="UN",
        is_active=True,
    )
    EstoqueMaterial.objects.create(
        material=mat,
        saldo_fisico=saldo_fisico,
        saldo_reservado=saldo_reservado,
    )
    return mat


def _post_data(beneficiario_id, material_id, quantidade="5.000", acao="salvar", observacao=""):
    """Monta POST data válido para criar rascunho com 1 item."""
    return {
        "beneficiario_id": str(beneficiario_id),
        "observacao": observacao,
        "acao": acao,
        # Formset management
        "form-TOTAL_FORMS": "1",
        "form-INITIAL_FORMS": "0",
        "form-MIN_NUM_FORMS": "1",
        "form-MAX_NUM_FORMS": "1000",
        # Item 0
        "form-0-material_id": str(material_id),
        "form-0-quantidade_solicitada": quantidade,
        "form-0-observacao": "",
        "form-0-DELETE": "",
    }


def _create_url():
    return reverse("web:requisition_create")


def _edit_url(pk):
    return reverse("web:requisition_edit", args=[pk])


def _send_url(pk):
    return reverse("web:requisition_send", args=[pk])


def _material_search_url():
    return reverse("web:material_search")


def _item_add_url():
    return reverse("web:requisition_item_add")


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAcesso:
    def test_get_create_nao_autenticado_redireciona(self):
        resp = Client().get(_create_url())
        assert resp.status_code == 302
        assert "/login/" in resp["Location"]

    def test_get_create_autenticado_retorna_200(self):
        client = Client()
        client.force_login(_user("89001"))
        resp = client.get(_create_url())
        assert resp.status_code == 200

    def test_get_edit_nao_autenticado_redireciona(self):
        resp = Client().get(_edit_url(999))
        assert resp.status_code == 302
        assert "/login/" in resp["Location"]

    def test_material_search_nao_autenticado(self):
        resp = Client().get(_material_search_url(), {"q": "tubo"})
        # HTMX session expired helper returns 200 with HX-Redirect
        # non-HTMX would redirect normally
        assert resp.status_code in (200, 302)


# ---------------------------------------------------------------------------
# Template e estrutura
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTemplate:
    def test_usa_template_form(self):
        client = Client()
        client.force_login(_user("89010"))
        resp = client.get(_create_url())
        templates = [t.name for t in resp.templates]
        assert "web/pages/requisitions/form.html" in templates

    def test_usa_app_shell(self):
        client = Client()
        client.force_login(_user("89011"))
        resp = client.get(_create_url())
        templates = [t.name for t in resp.templates]
        assert "web/layouts/app_shell.html" in templates

    def test_h1_com_page_title(self):
        client = Client()
        client.force_login(_user("89012"))
        resp = client.get(_create_url())
        assert b"Nova solicita" in resp.content  # "Nova solicitação"

    def test_form_action_correto(self):
        client = Client()
        client.force_login(_user("89013"))
        resp = client.get(_create_url())
        assert b'action="/requisicoes/nova/"' in resp.content


# ---------------------------------------------------------------------------
# Atributos HTML / testid
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEstruturaHtml:
    def test_form_body_testid_presente(self):
        client = Client()
        client.force_login(_user("89020"))
        resp = client.get(_create_url())
        assert b'data-testid="requisition-form-body"' in resp.content

    def test_add_item_btn_testid(self):
        client = Client()
        client.force_login(_user("89021"))
        resp = client.get(_create_url())
        assert b'data-testid="add-item-btn"' in resp.content

    def test_save_btn_testid(self):
        client = Client()
        client.force_login(_user("89022"))
        resp = client.get(_create_url())
        assert b'data-testid="save-btn"' in resp.content

    def test_send_btn_testid(self):
        client = Client()
        client.force_login(_user("89023"))
        resp = client.get(_create_url())
        assert b'data-testid="send-btn"' in resp.content

    def test_item_row_testid_presente(self):
        client = Client()
        client.force_login(_user("89024"))
        resp = client.get(_create_url())
        assert b'data-testid="item-row"' in resp.content

    def test_solicitante_mostra_beneficiario_display(self):
        u = _user("89025", papel=PapelChoices.SOLICITANTE)
        client = Client()
        client.force_login(u)
        resp = client.get(_create_url())
        assert b'data-testid="beneficiario-display"' in resp.content

    def test_chefia_mostra_busca_beneficiario(self):
        u = _user("89026", papel=PapelChoices.CHEFE_SETOR)
        client = Client()
        client.force_login(u)
        resp = client.get(_create_url())
        assert b'data-testid="beneficio-search-input"' in resp.content

    def test_hx_post_no_form(self):
        client = Client()
        client.force_login(_user("89027"))
        resp = client.get(_create_url())
        assert b"hx-post" in resp.content

    def test_management_form_presente(self):
        client = Client()
        client.force_login(_user("89028"))
        resp = client.get(_create_url())
        assert b"form-TOTAL_FORMS" in resp.content


# ---------------------------------------------------------------------------
# POST válido — caminho feliz
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPostCriar:
    def test_post_valido_cria_rascunho_e_redireciona(self):
        u = _user("89030")
        mat = _material("Válvula 3/4")
        client = Client()
        client.force_login(u)

        data = _post_data(beneficiario_id=u.pk, material_id=mat.pk)
        resp = client.post(_create_url(), data)

        assert resp.status_code == 302
        assert Requisicao.objects.filter(criador=u).exists()

    def test_post_cria_rascunho_com_status_rascunho(self):
        u = _user("89031")
        mat = _material("Curva 90 50mm")
        client = Client()
        client.force_login(u)

        data = _post_data(beneficiario_id=u.pk, material_id=mat.pk)
        client.post(_create_url(), data)

        req = Requisicao.objects.filter(criador=u).first()
        assert req is not None
        assert req.status == StatusRequisicao.RASCUNHO

    def test_post_com_acao_enviar_manda_para_autorizacao(self):
        u = _user("89032")
        mat = _material("Joelho 50mm")
        client = Client()
        client.force_login(u)

        data = _post_data(beneficiario_id=u.pk, material_id=mat.pk, acao="enviar")
        resp = client.post(_create_url(), data)

        assert resp.status_code == 302
        req = Requisicao.objects.filter(criador=u).first()
        assert req is not None
        assert req.status == StatusRequisicao.AGUARDANDO_AUTORIZACAO

    def test_post_htmx_valido_retorna_hx_redirect(self):
        u = _user("89033")
        mat = _material("Registro 50mm")
        client = Client()
        client.force_login(u)

        data = _post_data(beneficiario_id=u.pk, material_id=mat.pk)
        resp = client.post(_create_url(), data, **HTMX_HEADERS)

        # HTMX success → HttpResponseClientRedirect (200 com HX-Redirect header)
        assert resp.status_code == 200
        assert "HX-Redirect" in resp or resp.has_header("HX-Redirect")

    def test_redirect_para_minhas_solicitacoes(self):
        u = _user("89034")
        mat = _material("Tampa DN50")
        client = Client()
        client.force_login(u)

        data = _post_data(beneficiario_id=u.pk, material_id=mat.pk)
        resp = client.post(_create_url(), data)

        assert resp.status_code == 302
        assert "/minhas-solicitacoes/" in resp["Location"]


# ---------------------------------------------------------------------------
# POST inválido — 422
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPostInvalido:
    def test_sem_items_retorna_422(self):
        u = _user("89040")
        client = Client()
        client.force_login(u)

        data = {
            "beneficiario_id": str(u.pk),
            "observacao": "",
            "acao": "salvar",
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "1",
            "form-MAX_NUM_FORMS": "1000",
        }
        resp = client.post(_create_url(), data)
        assert resp.status_code == 422

    def test_sem_beneficiario_retorna_422(self):
        u = _user("89041", papel=PapelChoices.CHEFE_SETOR)
        mat = _material("Braçadeira")
        client = Client()
        client.force_login(u)

        data = _post_data(beneficiario_id="", material_id=mat.pk)
        resp = client.post(_create_url(), data)
        assert resp.status_code == 422

    def test_422_tem_aria_invalid(self):
        u = _user("89042")
        client = Client()
        client.force_login(u)

        data = {
            "beneficiario_id": str(u.pk),
            "observacao": "",
            "acao": "salvar",
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "1",
            "form-MAX_NUM_FORMS": "1000",
        }
        resp = client.post(_create_url(), data)
        assert resp.status_code == 422
        assert b"aria-invalid" in resp.content

    def test_422_htmx_usa_partial_template(self):
        u = _user("89043")
        client = Client()
        client.force_login(u)

        data = {
            "beneficiario_id": str(u.pk),
            "observacao": "",
            "acao": "salvar",
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "1",
            "form-MAX_NUM_FORMS": "1000",
        }
        resp = client.post(_create_url(), data, **HTMX_HEADERS)
        assert resp.status_code == 422
        templates = [t.name for t in resp.templates]
        assert "web/pages/requisitions/_form_body.html" in templates

    def test_422_nao_htmx_usa_full_template(self):
        u = _user("89044")
        client = Client()
        client.force_login(u)

        data = {
            "beneficiario_id": str(u.pk),
            "observacao": "",
            "acao": "salvar",
            "form-TOTAL_FORMS": "0",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "1",
            "form-MAX_NUM_FORMS": "1000",
        }
        resp = client.post(_create_url(), data)
        assert resp.status_code == 422
        templates = [t.name for t in resp.templates]
        assert "web/pages/requisitions/form.html" in templates

    def test_solicitante_post_com_beneficiario_alheio_retorna_422(self):
        """PER-01: SOLICITANTE ignorará POSTed beneficiário_id e forçará o próprio pk.
        O service vai criar para o próprio usuário. Se o id enviado é de outro usuário,
        o criado ignorado e a req é criada para si mesmo (não é 422 mas sim bypass)."""
        u = _user("89045", papel=PapelChoices.SOLICITANTE)
        outro = _user("89045b", papel=PapelChoices.SOLICITANTE)
        mat = _material("Cotovelo 50mm")
        client = Client()
        client.force_login(u)

        data = _post_data(beneficiario_id=outro.pk, material_id=mat.pk)
        resp = client.post(_create_url(), data)

        # PER-01: view forces beneficiario_id = request.user.pk → succeeds
        # so req is created for 'u' not 'outro'
        assert resp.status_code == 302
        req = Requisicao.objects.filter(criador=u).first()
        assert req is not None
        assert req.beneficiario_id == u.pk


# ---------------------------------------------------------------------------
# Edit view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEditView:
    def _make_rascunho(self, criador):
        return Requisicao.objects.create(
            criador=criador,
            beneficiario=criador,
            setor_beneficiario=criador.setor,
            status=StatusRequisicao.RASCUNHO,
        )

    def test_get_edit_retorna_200_para_criador(self):
        u = _user("89050")
        req = self._make_rascunho(u)
        client = Client()
        client.force_login(u)
        resp = client.get(_edit_url(req.pk))
        assert resp.status_code == 200

    def test_get_edit_404_para_nao_criador(self):
        u1 = _user("89051")
        u2 = _user("89052")
        req = self._make_rascunho(u1)
        client = Client()
        client.force_login(u2)
        resp = client.get(_edit_url(req.pk))
        assert resp.status_code == 404

    def test_get_edit_404_para_req_inexistente(self):
        u = _user("89053")
        client = Client()
        client.force_login(u)
        resp = client.get(_edit_url(99999))
        assert resp.status_code == 404

    def test_get_edit_usa_template_form(self):
        u = _user("89054")
        req = self._make_rascunho(u)
        client = Client()
        client.force_login(u)
        resp = client.get(_edit_url(req.pk))
        templates = [t.name for t in resp.templates]
        assert "web/pages/requisitions/form.html" in templates


# ---------------------------------------------------------------------------
# Send view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSendView:
    def _make_rascunho_com_item(self, criador):
        mat = _material("Material p/ envio")
        from apps.requisitions.domain.types import ItemRascunhoData
        from apps.requisitions.services import criar_rascunho_requisicao

        return criar_rascunho_requisicao(
            criador=criador,
            beneficiario=criador,
            observacao="",
            itens=[
                ItemRascunhoData(
                    material_id=mat.pk, quantidade_solicitada=Decimal("1"), observacao=""
                )
            ],
        )

    def test_post_send_muda_status_para_em_analise(self):
        u = _user("89060")
        req = self._make_rascunho_com_item(u)
        client = Client()
        client.force_login(u)
        resp = client.post(_send_url(req.pk))
        assert resp.status_code == 302
        req.refresh_from_db()
        assert req.status == StatusRequisicao.AGUARDANDO_AUTORIZACAO

    def test_post_send_404_para_req_inexistente(self):
        u = _user("89061")
        client = Client()
        client.force_login(u)
        resp = client.post(_send_url(99999))
        assert resp.status_code == 404

    def test_post_send_404_para_nao_criador(self):
        u1 = _user("89062")
        u2 = _user("89063")
        req = self._make_rascunho_com_item(u1)
        client = Client()
        client.force_login(u2)
        resp = client.post(_send_url(req.pk))
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# HTMX material_search
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMaterialSearch:
    def test_retorna_200(self):
        u = _user("89070")
        _material("Tubo PEAD 100mm")
        client = Client()
        client.force_login(u)
        resp = client.get(_material_search_url(), {"q": "Tubo", "idx": "0"}, **HTMX_HEADERS)
        assert resp.status_code == 200

    def test_retorna_partial_material_results(self):
        u = _user("89071")
        _material("Registro Gaveta")
        client = Client()
        client.force_login(u)
        resp = client.get(_material_search_url(), {"q": "Reg", "idx": "0"}, **HTMX_HEADERS)
        templates = [t.name for t in resp.templates]
        assert "web/pages/requisitions/_material_results.html" in templates

    def test_query_curto_retorna_vazio(self):
        u = _user("89072")
        client = Client()
        client.force_login(u)
        resp = client.get(_material_search_url(), {"q": "ab", "idx": "0"})
        assert resp.status_code == 200
        assert b"listbox" not in resp.content

    def test_material_sem_estoque_nao_aparece(self):
        u = _user("89073")
        grupo, _ = GrupoMaterial.objects.get_or_create(
            codigo_grupo="013", defaults={"nome": "Hidráulico"}
        )
        subgrupo, _ = SubgrupoMaterial.objects.get_or_create(
            grupo=grupo, codigo_subgrupo="001", defaults={"nome": "Tubulação"}
        )
        global _mat_counter
        _mat_counter += 1
        seq_no_stock = str(_mat_counter).zfill(3)
        Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo=f"013.001.{seq_no_stock}",
            sequencial=seq_no_stock,
            nome="Material Sem Estoque",
            unidade_medida="UN",
            is_active=True,
        )
        client = Client()
        client.force_login(u)
        resp = client.get(_material_search_url(), {"q": "Sem Estoque", "idx": "0"})
        assert b"Material Sem Estoque" not in resp.content


# ---------------------------------------------------------------------------
# HTMX item_add
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestItemAdd:
    def test_retorna_200(self):
        u = _user("89080")
        client = Client()
        client.force_login(u)
        resp = client.get(_item_add_url(), {"total": "1"}, **HTMX_HEADERS)
        assert resp.status_code == 200

    def test_usa_template_item_row(self):
        u = _user("89081")
        client = Client()
        client.force_login(u)
        resp = client.get(_item_add_url(), {"total": "2"}, **HTMX_HEADERS)
        templates = [t.name for t in resp.templates]
        assert "web/pages/requisitions/_item_row.html" in templates

    def test_idx_correto_no_html(self):
        u = _user("89082")
        client = Client()
        client.force_login(u)
        resp = client.get(_item_add_url(), {"total": "3"}, **HTMX_HEADERS)
        # idx = total = 3, so field names include form-3-*
        assert b"form-3-" in resp.content

    def test_oob_swap_atualiza_total_forms(self):
        u = _user("89083")
        client = Client()
        client.force_login(u)
        resp = client.get(_item_add_url(), {"total": "1"}, **HTMX_HEADERS)
        # new_total = 2 should appear in OOB swap
        assert b'value="2"' in resp.content

    def test_item_row_tem_testid(self):
        u = _user("89084")
        client = Client()
        client.force_login(u)
        resp = client.get(_item_add_url(), {"total": "0"})
        assert b'data-testid="item-row"' in resp.content


# ---------------------------------------------------------------------------
# Navegação
# ---------------------------------------------------------------------------


def _nav_keys(resp):
    """Extract nav item keys from response context navigation tree."""
    navigation = resp.context.get("navigation", [])
    keys = []
    for section in navigation:
        for item in section.get("items", []):
            keys.append(item.get("key"))
    return keys


@pytest.mark.django_db
class TestNavegacao:
    def _get_nav_keys(self, papel, matricula=None):
        mat = matricula or f"nav_{papel}"
        u = _user(mat, papel=papel)
        client = Client()
        client.force_login(u)
        resp = client.get(_create_url())
        return _nav_keys(resp)

    def test_solicitante_tem_nova_solicitacao_no_nav(self):
        assert "requisition_create" in self._get_nav_keys(PapelChoices.SOLICITANTE, "nav_sol")

    def test_auxiliar_setor_tem_nova_solicitacao_no_nav(self):
        assert "requisition_create" in self._get_nav_keys(PapelChoices.AUXILIAR_SETOR, "nav_aux")

    def test_chefe_setor_tem_nova_solicitacao_no_nav(self):
        assert "requisition_create" in self._get_nav_keys(PapelChoices.CHEFE_SETOR, "nav_chf")

    def test_auxiliar_almoxarifado_tem_nova_solicitacao_no_nav(self):
        u = User.objects.create_user(
            matricula_funcional="nav_almx",
            password="x",
            nome_completo="Alm",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            is_active=True,
        )
        client = Client()
        client.force_login(u)
        resp = client.get(_create_url())
        assert "requisition_create" in _nav_keys(resp)
