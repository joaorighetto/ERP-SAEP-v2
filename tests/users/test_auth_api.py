import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.models import PapelChoices, Setor, User


@pytest.mark.django_db
class TestAuthAPI:
    @staticmethod
    def _criar_usuario_com_setor(*, matricula: str = "10001") -> User:
        user = User.objects.create_user(
            matricula_funcional=matricula,
            password="senha-segura-123",
            nome_completo="Usuario Auth",
            papel=PapelChoices.CHEFE_SETOR,
            is_active=True,
        )
        setor = Setor.objects.create(nome=f"Setor {matricula}", chefe_responsavel=user)
        user.setor = setor
        user.save(update_fields=["setor"])
        return user

    @staticmethod
    def _csrf_client():
        client = APIClient(enforce_csrf_checks=True)
        csrf_response = client.get(reverse("auth-csrf"))
        return client, csrf_response.data["csrf_token"]

    def test_me_sem_sessao_valida_retorna_401(self):
        client = APIClient()

        response = client.get(reverse("auth-me"))

        assert response.status_code == 401
        assert response.data["error"]["code"] == "not_authenticated"

    def test_me_com_sessao_valida_retorna_payload_canonico(self):
        user = self._criar_usuario_com_setor()
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(reverse("auth-me"))

        assert response.status_code == 200
        assert response.data == {
            "id": user.id,
            "matricula_funcional": "10001",
            "nome_completo": "Usuario Auth",
            "papel": PapelChoices.CHEFE_SETOR,
            "setor": {
                "id": user.setor_id,
                "nome": "Setor 10001",
            },
            "is_authenticated": True,
        }

    def test_csrf_retorna_token_e_cookie(self):
        client = APIClient()

        response = client.get(reverse("auth-csrf"))

        assert response.status_code == 200
        assert response.data["csrf_token"]
        assert "csrftoken" in response.cookies

    def test_login_com_matricula_e_senha_validas_cria_sessao_e_retorna_payload(self):
        user = self._criar_usuario_com_setor()
        client, csrf_token = self._csrf_client()

        response = client.post(
            reverse("auth-login"),
            {
                "matricula_funcional": "10001",
                "password": "senha-segura-123",
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        assert response.status_code == 200
        assert response.data["id"] == user.id
        assert response.data["matricula_funcional"] == "10001"
        assert response.data["is_authenticated"] is True

        me_response = client.get(reverse("auth-me"))
        assert me_response.status_code == 200
        assert me_response.data["id"] == user.id

    def test_login_com_credenciais_invalidas_retorna_401(self):
        self._criar_usuario_com_setor()
        client, csrf_token = self._csrf_client()

        response = client.post(
            reverse("auth-login"),
            {
                "matricula_funcional": "10001",
                "password": "senha-invalida",
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        assert response.status_code == 401
        assert response.data["error"]["code"] == "authentication_failed"

    def test_login_com_usuario_inativo_retorna_401(self):
        user = self._criar_usuario_com_setor()
        user.is_active = False
        user.save(update_fields=["is_active"])
        client, csrf_token = self._csrf_client()

        response = client.post(
            reverse("auth-login"),
            {
                "matricula_funcional": "10001",
                "password": "senha-segura-123",
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        assert response.status_code == 401
        assert response.data["error"]["code"] == "authentication_failed"

    def test_login_sem_csrf_valido_retorna_403(self):
        self._criar_usuario_com_setor()
        client = APIClient(enforce_csrf_checks=True)

        response = client.post(
            reverse("auth-login"),
            {
                "matricula_funcional": "10001",
                "password": "senha-segura-123",
            },
            format="json",
        )

        assert response.status_code == 403

    def test_logout_com_sessao_valida_retorna_204_e_invalida_sessao(self):
        self._criar_usuario_com_setor()
        client, csrf_token = self._csrf_client()
        login_response = client.post(
            reverse("auth-login"),
            {
                "matricula_funcional": "10001",
                "password": "senha-segura-123",
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        assert login_response.status_code == 200
        csrf_token = client.cookies["csrftoken"].value

        logout_response = client.post(
            reverse("auth-logout"),
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        assert logout_response.status_code == 204
        me_response = client.get(reverse("auth-me"))
        assert me_response.status_code == 401

    def test_logout_sem_sessao_valida_retorna_204(self):
        client, csrf_token = self._csrf_client()

        response = client.post(
            reverse("auth-logout"),
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        assert response.status_code == 204

    def test_logout_sem_csrf_valido_retorna_403(self):
        client = APIClient(enforce_csrf_checks=True)

        response = client.post(reverse("auth-logout"), format="json")

        assert response.status_code == 403

    def test_login_sem_campos_obrigatorios_retorna_400(self):
        client, csrf_token = self._csrf_client()

        response = client.post(
            reverse("auth-login"),
            {},  # payload vazio
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
