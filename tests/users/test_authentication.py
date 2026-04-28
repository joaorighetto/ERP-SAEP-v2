from django.contrib.auth import authenticate
from django.test import TestCase

from apps.users.backends import MatriculaBackend
from apps.users.models import User


class TestMatriculaAuthentication(TestCase):
    """Testes para autenticação por matrícula funcional."""

    def setUp(self):
        self.user_data = {
            "matricula_funcional": "MAT001",
            "password": "senha_segura_123",
            "nome_completo": "João Silva",
        }
        self.user = User.objects.create_user(**self.user_data)

    def test_autenticacao_com_matricula_e_senha_validas(self):
        """Autentica usuário com matrícula e senha válidas."""
        user = authenticate(
            matricula_funcional=self.user_data["matricula_funcional"],
            password=self.user_data["password"],
        )
        assert user is not None
        assert user.pk == self.user.pk
        assert user.matricula_funcional == self.user_data["matricula_funcional"]

    def test_autenticacao_com_username_padrao_do_django(self):
        """Autentica usuário pelo fluxo padrão do Django usando username."""
        user = authenticate(
            username=self.user_data["matricula_funcional"],
            password=self.user_data["password"],
        )
        assert user is not None
        assert user.pk == self.user.pk

    def test_autenticacao_falha_com_matricula_incorreta(self):
        """Retorna None quando matrícula não existe."""
        user = authenticate(
            matricula_funcional="MATRICULA_INVALIDA",
            password=self.user_data["password"],
        )
        assert user is None

    def test_autenticacao_falha_com_senha_incorreta(self):
        """Retorna None quando senha está incorreta."""
        user = authenticate(
            matricula_funcional=self.user_data["matricula_funcional"],
            password="senha_errada",
        )
        assert user is None

    def test_autenticacao_falha_sem_parametros(self):
        """Retorna None quando parâmetros estão vazios."""
        user = authenticate(matricula_funcional="", password="")
        assert user is None

    def test_usuario_inativo_nao_autentica(self):
        """Usuário inativo não consegue se autenticar."""
        self.user.is_active = False
        self.user.save()

        user = authenticate(
            matricula_funcional=self.user_data["matricula_funcional"],
            password=self.user_data["password"],
        )
        assert user is None

    def test_usuario_ativo_apos_desativar_e_reativar(self):
        """Usuário desativado e reativado consegue se autenticar novamente."""
        self.user.is_active = False
        self.user.save()

        user = authenticate(
            matricula_funcional=self.user_data["matricula_funcional"],
            password=self.user_data["password"],
        )
        assert user is None

        self.user.is_active = True
        self.user.save()

        user = authenticate(
            matricula_funcional=self.user_data["matricula_funcional"],
            password=self.user_data["password"],
        )
        assert user is not None

    def test_multiplos_usuarios_autenticacao_isolada(self):
        """Dois usuários não se confundem na autenticação."""
        user2 = User.objects.create_user(
            matricula_funcional="MAT002",
            password="outra_senha_123",
            nome_completo="Maria Santos",
        )

        auth1 = authenticate(
            matricula_funcional=self.user_data["matricula_funcional"],
            password=self.user_data["password"],
        )
        auth2 = authenticate(
            matricula_funcional="MAT002",
            password="outra_senha_123",
        )

        assert auth1.pk == self.user.pk
        assert auth2.pk == user2.pk
        assert auth1.pk != auth2.pk

    def test_autenticacao_case_sensitive_em_matricula(self):
        """Matrícula é case-sensitive na busca (comportamento padrão)."""
        user = authenticate(
            matricula_funcional=self.user_data["matricula_funcional"].lower(),
            password=self.user_data["password"],
        )
        assert user is None

    def test_sensibilidade_a_espacos_em_matricula(self):
        """Espaços em torno da matrícula não devem fazer match."""
        user = authenticate(
            matricula_funcional=f" {self.user_data['matricula_funcional']} ",
            password=self.user_data["password"],
        )
        assert user is None

    def test_get_user_por_id(self):
        """Backend consegue recuperar usuário por ID (necessário para sessões)."""
        backend = MatriculaBackend()
        user = backend.get_user(self.user.pk)
        assert user is not None
        assert user.pk == self.user.pk

    def test_get_user_com_id_invalido(self):
        """Backend retorna None para ID que não existe."""
        backend = MatriculaBackend()
        user = backend.get_user(99999)
        assert user is None
