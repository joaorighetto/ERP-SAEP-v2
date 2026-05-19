"""Testes de contrato — Auth HTML server-rendered (PR3 / issue #38).

Cobre:
- GET /login/: 200, template, campos, CSRF, acessibilidade
- POST /login/: credenciais válidas, inválidas, campos vazios, next, usuário inativo
- GET /login/ autenticado: redirect
- GET/POST /logout/: encerramento de sessão, idempotência
- GET /logout/concluido/: página pública
"""

import pytest
from django.test import Client
from django.urls import reverse

from apps.users.models import PapelChoices, Setor, User


@pytest.fixture
def client():
    return Client()


def _criar_usuario(
    *,
    matricula="88001",
    password="senha-segura-test",
    papel=PapelChoices.SOLICITANTE,
    is_active=True,
):
    user = User.objects.create_user(
        matricula_funcional=matricula,
        password=password,
        nome_completo="Usuário Auth Teste",
        papel=papel,
        is_active=is_active,
    )
    setor = Setor.objects.create(nome=f"Setor {matricula}", chefe_responsavel=user)
    user.setor = setor
    user.save(update_fields=["setor"])
    return user


# ---------------------------------------------------------------------------
# GET /login/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLoginGet:
    def test_get_retorna_200(self, client):
        url = reverse("web:login")
        res = client.get(url)
        assert res.status_code == 200

    def test_usa_template_correto(self, client):
        url = reverse("web:login")
        res = client.get(url)
        assert "web/pages/auth/login.html" in [t.name for t in res.templates]

    def test_usa_auth_shell(self, client):
        url = reverse("web:login")
        res = client.get(url)
        template_names = [t.name for t in res.templates]
        assert "web/layouts/auth_shell.html" in template_names

    def test_csrf_presente(self, client):
        url = reverse("web:login")
        res = client.get(url)
        content = res.content.decode()
        assert "csrfmiddlewaretoken" in content

    def test_campo_matricula_presente(self, client):
        url = reverse("web:login")
        res = client.get(url)
        content = res.content.decode()
        assert 'name="matricula_funcional"' in content

    def test_campo_password_presente(self, client):
        url = reverse("web:login")
        res = client.get(url)
        content = res.content.decode()
        assert 'name="password"' in content
        assert 'type="password"' in content

    def test_label_matricula_presente(self, client):
        url = reverse("web:login")
        res = client.get(url)
        content = res.content.decode()
        assert "Matrícula funcional" in content

    def test_label_senha_presente(self, client):
        url = reverse("web:login")
        res = client.get(url)
        content = res.content.decode()
        assert "Senha" in content

    def test_botao_submit_type_correto(self, client):
        url = reverse("web:login")
        res = client.get(url)
        content = res.content.decode()
        assert 'type="submit"' in content

    def test_usuario_autenticado_e_redirecionado(self, client):
        user = _criar_usuario()
        client.force_login(user)
        url = reverse("web:login")
        res = client.get(url)
        assert res.status_code == 302
        assert res["Location"] == reverse("web:home")

    def test_sem_erro_na_carga_inicial(self, client):
        url = reverse("web:login")
        res = client.get(url)
        content = res.content.decode()
        assert 'data-testid="auth-error"' not in content


# ---------------------------------------------------------------------------
# POST /login/ — credenciais válidas
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLoginPostValido:
    def test_credenciais_validas_criam_sessao_e_redirecionam(self, client):
        _criar_usuario(matricula="88002", password="senha-valida")
        url = reverse("web:login")
        res = client.post(url, {"matricula_funcional": "88002", "password": "senha-valida"})
        assert res.status_code == 302
        assert res["Location"] == reverse("web:home")
        assert "_auth_user_id" in client.session

    def test_next_interno_valido_e_respeitado(self, client):
        _criar_usuario(matricula="88003", password="senha-valida")
        url = reverse("web:login")
        next_url = reverse("web:requisitions_mine")
        res = client.post(
            url,
            {"matricula_funcional": "88003", "password": "senha-valida", "next": next_url},
        )
        assert res.status_code == 302
        assert res["Location"] == next_url

    def test_next_externo_e_ignorado(self, client):
        _criar_usuario(matricula="88004", password="senha-valida")
        url = reverse("web:login")
        res = client.post(
            url,
            {
                "matricula_funcional": "88004",
                "password": "senha-valida",
                "next": "https://evil.example.com/steal",
            },
        )
        assert res.status_code == 302
        assert "evil.example.com" not in res["Location"]
        assert res["Location"] == reverse("web:home")


# ---------------------------------------------------------------------------
# POST /login/ — credenciais inválidas / erro de domínio
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLoginPostInvalido:
    def test_senha_errada_retorna_200_com_alerta(self, client):
        _criar_usuario(matricula="88010", password="senha-certa")
        url = reverse("web:login")
        res = client.post(url, {"matricula_funcional": "88010", "password": "senha-errada"})
        assert res.status_code == 200
        content = res.content.decode()
        assert 'data-testid="auth-error"' in content

    def test_mensagem_erro_generica(self, client):
        _criar_usuario(matricula="88011", password="senha-certa")
        url = reverse("web:login")
        res = client.post(url, {"matricula_funcional": "88011", "password": "senha-errada"})
        content = res.content.decode()
        assert "Matrícula funcional ou senha inválidas." in content

    def test_sessao_nao_criada_em_falha(self, client):
        _criar_usuario(matricula="88012", password="senha-certa")
        url = reverse("web:login")
        client.post(url, {"matricula_funcional": "88012", "password": "errada"})
        assert "_auth_user_id" not in client.session

    def test_matricula_inexistente_retorna_200_com_alerta(self, client):
        url = reverse("web:login")
        res = client.post(url, {"matricula_funcional": "nao-existe-99999", "password": "qualquer"})
        assert res.status_code == 200
        assert 'data-testid="auth-error"' in res.content.decode()

    def test_usuario_inativo_retorna_alerta_generico(self, client):
        _criar_usuario(matricula="88013", password="senha-certa", is_active=False)
        url = reverse("web:login")
        res = client.post(url, {"matricula_funcional": "88013", "password": "senha-certa"})
        assert res.status_code == 200
        content = res.content.decode()
        assert 'data-testid="auth-error"' in content
        # Não revela motivo específico
        assert "inativo" not in content.lower()
        assert "_auth_user_id" not in client.session

    def test_campos_vazios_retornam_erros_de_campo(self, client):
        url = reverse("web:login")
        res = client.post(url, {"matricula_funcional": "", "password": ""})
        assert res.status_code == 422
        content = res.content.decode()
        assert "aria-invalid" in content

    def test_campo_invalido_tem_aria_describedby(self, client):
        url = reverse("web:login")
        res = client.post(url, {"matricula_funcional": "", "password": ""})
        content = res.content.decode()
        assert "aria-describedby" in content


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLogout:
    def test_post_logout_encerra_sessao(self, client):
        user = _criar_usuario(matricula="88020")
        client.force_login(user)
        assert "_auth_user_id" in client.session
        url = reverse("web:logout")
        res = client.post(url)
        assert res.status_code == 302
        assert "_auth_user_id" not in client.session

    def test_post_logout_redireciona_para_logged_out(self, client):
        user = _criar_usuario(matricula="88021")
        client.force_login(user)
        url = reverse("web:logout")
        res = client.post(url)
        assert res["Location"] == reverse("web:logged_out")

    def test_get_logout_nao_encerra_sessao(self, client):
        user = _criar_usuario(matricula="88022")
        client.force_login(user)
        url = reverse("web:logout")
        res = client.get(url)
        # GET não mata sessão — redireciona sem logout
        assert res.status_code == 302
        assert "_auth_user_id" in client.session

    def test_get_logout_redireciona_para_login(self, client):
        user = _criar_usuario(matricula="88023")
        client.force_login(user)
        url = reverse("web:logout")
        res = client.get(url)
        assert res["Location"] == reverse("web:login")

    def test_post_logout_usuario_nao_autenticado_e_seguro(self, client):
        url = reverse("web:logout")
        res = client.post(url)
        # Idempotente: não deve dar 500
        assert res.status_code in (302, 200)


# ---------------------------------------------------------------------------
# Página logged_out
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLoggedOutPage:
    def test_get_retorna_200(self, client):
        url = reverse("web:logged_out")
        res = client.get(url)
        assert res.status_code == 200

    def test_usa_template_correto(self, client):
        url = reverse("web:logged_out")
        res = client.get(url)
        assert "web/pages/auth/logged_out.html" in [t.name for t in res.templates]

    def test_contem_link_para_login(self, client):
        url = reverse("web:logged_out")
        res = client.get(url)
        content = res.content.decode()
        assert reverse("web:login") in content
