"""Testes de contrato da fundação do frontend server-rendered (PR1).

Cobre:
- Página home: GET 200, template, shell targets, acessibilidade
- Auth: unauthenticated redirect
- Navegação: itens por papel
- Helpers HTMX: contratos de resposta
"""

import pytest
from django.test import Client
from django.urls import reverse

from apps.users.models import PapelChoices, Setor, User


@pytest.fixture
def client():
    return Client()


def _criar_usuario(*, papel=PapelChoices.SOLICITANTE, matricula="99001"):
    user = User.objects.create_user(
        matricula_funcional=matricula,
        password="senha-segura-test",
        nome_completo="Usuario Teste",
        papel=papel,
        is_active=True,
    )
    setor = Setor.objects.create(nome=f"Setor {matricula}", chefe_responsavel=user)
    user.setor = setor
    user.save(update_fields=["setor"])
    return user


@pytest.mark.django_db
class TestHomePage:
    def test_get_home_autenticado_retorna_200(self, client):
        user = _criar_usuario()
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        assert resp.status_code == 200

    def test_get_home_usa_template_correto(self, client):
        user = _criar_usuario()
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        assert "web/pages/home.html" in [t.name for t in resp.templates]

    def test_get_home_usa_app_shell(self, client):
        user = _criar_usuario()
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        template_names = [t.name for t in resp.templates]
        assert "web/layouts/app_shell.html" in template_names

    def test_get_home_nao_autenticado_redireciona_para_login(self, client):
        resp = client.get(reverse("web:home"))
        assert resp.status_code == 302
        assert "/login/" in resp["Location"]

    def test_shell_contem_main_content(self, client):
        user = _criar_usuario()
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        content = resp.content.decode()
        assert 'id="main-content"' in content

    def test_shell_contem_global_feedback(self, client):
        user = _criar_usuario()
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        content = resp.content.decode()
        assert 'id="global-feedback"' in content

    def test_shell_contem_global_errors(self, client):
        user = _criar_usuario()
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        content = resp.content.decode()
        assert 'id="global-errors"' in content

    def test_shell_contem_modal_root(self, client):
        user = _criar_usuario()
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        content = resp.content.decode()
        assert 'id="modal-root"' in content

    def test_shell_contem_skip_link_para_main_content(self, client):
        user = _criar_usuario()
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        content = resp.content.decode()
        assert 'href="#main-content"' in content

    def test_shell_contem_css_compilado(self, client):
        user = _criar_usuario()
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        content = resp.content.decode()
        assert "web/dist/app.css" in content

    def test_shell_contem_aria_live_polite_em_feedback(self, client):
        user = _criar_usuario()
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        content = resp.content.decode()
        assert 'aria-live="polite"' in content

    def test_shell_contem_aria_live_assertive_em_errors(self, client):
        user = _criar_usuario()
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        content = resp.content.decode()
        assert 'aria-live="assertive"' in content

    def test_nav_tem_aria_label(self, client):
        user = _criar_usuario()
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        content = resp.content.decode()
        assert 'aria-label="Navegação principal"' in content

    def test_hx_headers_csrf_presentes(self, client):
        user = _criar_usuario()
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        content = resp.content.decode()
        assert "X-CSRFToken" in content

    def test_htmx_script_presente(self, client):
        user = _criar_usuario()
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        content = resp.content.decode()
        assert "htmx" in content.lower()


@pytest.mark.django_db
class TestNavegacaoPorPapel:
    def test_solicitante_ve_nova_solicitacao(self, client):
        user = _criar_usuario(papel=PapelChoices.SOLICITANTE, matricula="99002")
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        content = resp.content.decode()
        assert "Nova solicitação" in content

    def test_solicitante_ve_minhas_solicitacoes(self, client):
        user = _criar_usuario(papel=PapelChoices.SOLICITANTE, matricula="99003")
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        content = resp.content.decode()
        assert "Minhas solicitações" in content

    def test_chefe_setor_ve_aprovacoes_pendentes(self, client):
        user = _criar_usuario(papel=PapelChoices.CHEFE_SETOR, matricula="99004")
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        content = resp.content.decode()
        assert "Aprovações pendentes" in content

    def test_auxiliar_almoxarifado_ve_fila_atendimento(self, client):
        user = _criar_usuario(papel=PapelChoices.AUXILIAR_ALMOXARIFADO, matricula="99005")
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        content = resp.content.decode()
        assert "Fila de atendimento" in content

    def test_auxiliar_almoxarifado_ve_minhas_solicitacoes(self, client):
        user = _criar_usuario(papel=PapelChoices.AUXILIAR_ALMOXARIFADO, matricula="99005")
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        content = resp.content.decode()
        assert "Minhas solicitações" in content

    def test_chefe_almoxarifado_ve_fila_atendimento(self, client):
        user = _criar_usuario(papel=PapelChoices.CHEFE_ALMOXARIFADO, matricula="99006")
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        content = resp.content.decode()
        assert "Fila de atendimento" in content

    def test_chefe_almoxarifado_ve_minhas_solicitacoes(self, client):
        user = _criar_usuario(papel=PapelChoices.CHEFE_ALMOXARIFADO, matricula="99006")
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        content = resp.content.decode()
        assert "Minhas solicitações" in content

    def test_solicitante_nao_ve_fila_atendimento(self, client):
        user = _criar_usuario(papel=PapelChoices.SOLICITANTE, matricula="99007")
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        content = resp.content.decode()
        assert "Fila de atendimento" not in content

    def test_almoxarife_nao_ve_aprovacoes_pendentes(self, client):
        user = _criar_usuario(papel=PapelChoices.AUXILIAR_ALMOXARIFADO, matricula="99008")
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        content = resp.content.decode()
        assert "Aprovações pendentes" not in content

    def test_auxiliar_setor_ve_solicitacoes(self, client):
        user = _criar_usuario(papel=PapelChoices.AUXILIAR_SETOR, matricula="99009")
        client.force_login(user)
        resp = client.get(reverse("web:home"))
        content = resp.content.decode()
        assert "Minhas solicitações" in content


@pytest.mark.django_db
class TestHtmxHelpers:
    def test_htmx_redirect_retorna_hx_redirect_header(self):
        from apps.web.htmx import htmx_redirect

        resp = htmx_redirect("/destino/")
        assert resp.status_code == 200
        assert resp["HX-Redirect"] == "/destino/"

    def test_htmx_refresh_retorna_hx_refresh_header(self):
        from apps.web.htmx import htmx_refresh

        resp = htmx_refresh()
        assert resp["HX-Refresh"] == "true"

    def test_htmx_session_expired_retorna_redirect_para_login(self):
        from apps.web.htmx import htmx_session_expired

        resp = htmx_session_expired("/login/")
        assert resp["HX-Redirect"] == "/login/"

    def test_htmx_validation_error_retorna_422(self):
        from django.http import HttpRequest

        from apps.web.htmx import htmx_validation_error

        request = HttpRequest()
        request.method = "POST"
        resp = htmx_validation_error(request, "web/pages/home.html", {})
        assert resp.status_code == 422

    def test_htmx_forbidden_retorna_403(self):
        from apps.web.htmx import htmx_forbidden

        resp = htmx_forbidden(None)
        assert resp.status_code == 403

    def test_htmx_conflict_retorna_409(self):
        from apps.web.htmx import htmx_conflict

        resp = htmx_conflict(None)
        assert resp.status_code == 409
