import pytest
from django.contrib.auth import authenticate
from django.db import IntegrityError

from apps.users.models import User


@pytest.mark.django_db
class TestUserModel:
    def test_criar_usuario_ativo_com_matricula_unica(self):
        user = User.objects.create_user(
            matricula_funcional="12345",
            password="testpass123",
            nome_completo="João Silva",
            email="joao@example.com",
        )

        assert user.matricula_funcional == "12345"
        assert user.nome_completo == "João Silva"
        assert user.email == "joao@example.com"
        assert user.is_active is True
        assert user.is_staff is False
        assert user.check_password("testpass123")

    def test_impedir_matricula_duplicada(self):
        User.objects.create_user(
            matricula_funcional="12345",
            password="testpass123",
            nome_completo="João Silva",
        )

        with pytest.raises(IntegrityError):
            User.objects.create_user(
                matricula_funcional="12345",
                password="testpass123",
                nome_completo="Maria Silva",
            )

    def test_cpf_e_telefone_nao_existem_no_modelo(self):
        assert not hasattr(User, "cpf")
        assert not hasattr(User, "telefone")

    def test_usuario_inativo_nao_e_apto_para_acesso(self):
        user = User.objects.create_user(
            matricula_funcional="12345",
            password="testpass123",
            nome_completo="João Silva",
        )
        user.is_active = False
        user.save()

        assert user.is_active is False

    def test_usuario_inativo_nao_autentica(self):
        User.objects.create_user(
            matricula_funcional="12345",
            password="testpass123",
            nome_completo="João Silva",
            is_active=False,
        )

        result = authenticate(
            matricula_funcional="12345",
            password="testpass123",
        )
        assert result is None

    def test_criar_superuser(self):
        user = User.objects.create_superuser(
            matricula_funcional="admin",
            password="adminpass123",
        )

        assert user.is_superuser is True
        assert user.is_staff is True
        assert user.is_active is True

    def test_username_field_e_matricula_funcional(self):
        assert User.USERNAME_FIELD == "matricula_funcional"

    def test_required_fields_contem_nome_completo(self):
        assert "nome_completo" in User.REQUIRED_FIELDS

    def test_str_representation(self):
        user = User.objects.create_user(
            matricula_funcional="12345",
            password="testpass123",
            nome_completo="João Silva",
        )

        assert str(user) == "12345 - João Silva"
