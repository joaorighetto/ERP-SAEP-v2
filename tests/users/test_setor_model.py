import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from apps.users.models import Setor, User


@pytest.mark.django_db
class TestSetorModel:
    def test_criar_setor_com_chefe_responsavel(self):
        chefe = User.objects.create_user(
            matricula_funcional="12345",
            password="testpass123",
            nome_completo="João Silva",
        )
        setor = Setor.objects.create(
            nome="Almoxarifado",
            chefe_responsavel=chefe,
        )

        assert setor.nome == "Almoxarifado"
        assert setor.chefe_responsavel == chefe
        assert setor.is_active is True

    def test_impedir_setor_sem_chefe(self):
        setor = Setor(nome="Almoxarifado", chefe_responsavel=None)

        with pytest.raises(ValidationError):
            setor.full_clean()

    def test_impedir_setor_sem_chefe_no_banco(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            Setor.objects.bulk_create(
                [
                    Setor(
                        nome="Almoxarifado",
                        chefe_responsavel=None,
                    )
                ]
            )

    def test_impedir_que_mesmo_chefe_administre_dois_setores(self):
        chefe = User.objects.create_user(
            matricula_funcional="12345",
            password="testpass123",
            nome_completo="João Silva",
        )

        Setor.objects.create(
            nome="Almoxarifado",
            chefe_responsavel=chefe,
        )

        setor2_data = {
            "nome": "Manutenção",
            "chefe_responsavel": chefe,
        }

        with pytest.raises(IntegrityError):
            Setor.objects.create(**setor2_data)

    def test_impedir_que_mesmo_chefe_administre_dois_setores_no_banco(self):
        chefe = User.objects.create_user(
            matricula_funcional="12345",
            password="testpass123",
            nome_completo="João Silva",
        )

        Setor.objects.create(
            nome="Almoxarifado",
            chefe_responsavel=chefe,
        )

        with pytest.raises(IntegrityError), transaction.atomic():
            Setor.objects.bulk_create(
                [
                    Setor(
                        nome="Manutenção",
                        chefe_responsavel=chefe,
                    )
                ]
            )

    def test_impedir_nome_de_setor_duplicado(self):
        chefe1 = User.objects.create_user(
            matricula_funcional="12345",
            password="testpass123",
            nome_completo="João Silva",
        )
        chefe2 = User.objects.create_user(
            matricula_funcional="54321",
            password="testpass123",
            nome_completo="Maria Silva",
        )

        Setor.objects.create(
            nome="Almoxarifado",
            chefe_responsavel=chefe1,
        )

        with pytest.raises(IntegrityError):
            Setor.objects.create(
                nome="Almoxarifado",
                chefe_responsavel=chefe2,
            )

    def test_impedir_nome_de_setor_duplicado_no_banco(self):
        chefe1 = User.objects.create_user(
            matricula_funcional="12345",
            password="testpass123",
            nome_completo="João Silva",
        )
        chefe2 = User.objects.create_user(
            matricula_funcional="54321",
            password="testpass123",
            nome_completo="Maria Silva",
        )

        Setor.objects.create(
            nome="Almoxarifado",
            chefe_responsavel=chefe1,
        )

        with pytest.raises(IntegrityError), transaction.atomic():
            Setor.objects.bulk_create(
                [
                    Setor(
                        nome="Almoxarifado",
                        chefe_responsavel=chefe2,
                    )
                ]
            )

    def test_setor_inativo_permanece_em_historico(self):
        chefe = User.objects.create_user(
            matricula_funcional="12345",
            password="testpass123",
            nome_completo="João Silva",
        )
        setor = Setor.objects.create(
            nome="Almoxarifado",
            chefe_responsavel=chefe,
            is_active=False,
        )

        assert setor.is_active is False
        assert Setor.objects.filter(pk=setor.pk).exists()

    def test_str_representation(self):
        chefe = User.objects.create_user(
            matricula_funcional="12345",
            password="testpass123",
            nome_completo="João Silva",
        )
        setor = Setor.objects.create(
            nome="Almoxarifado",
            chefe_responsavel=chefe,
        )

        assert str(setor) == "Almoxarifado (Chefe: 12345)"

    def test_clean_aceita_quando_chefe_pertence_ao_proprio_setor(self):
        chefe = User.objects.create_user(
            matricula_funcional="12345",
            password="testpass123",
            nome_completo="João Silva",
        )
        setor = Setor.objects.create(
            nome="Almoxarifado",
            chefe_responsavel=chefe,
        )
        chefe.setor = setor
        chefe.save(update_fields=["setor"])

        setor.full_clean()

    def test_clean_rejeita_quando_chefe_pertence_a_outro_setor(self):
        chefe_a = User.objects.create_user(
            matricula_funcional="12345",
            password="testpass123",
            nome_completo="João Silva",
        )
        chefe_b = User.objects.create_user(
            matricula_funcional="54321",
            password="testpass123",
            nome_completo="Maria Silva",
        )
        setor_a = Setor.objects.create(
            nome="Almoxarifado",
            chefe_responsavel=chefe_a,
        )
        setor_b = Setor.objects.create(
            nome="Manutenção",
            chefe_responsavel=chefe_b,
        )
        chefe_a.setor = setor_b
        chefe_a.save(update_fields=["setor"])

        with pytest.raises(ValidationError):
            setor_a.clean()
        with pytest.raises(ValidationError):
            setor_a.full_clean()

    def test_full_clean_rejeita_setor_sem_chefe_responsavel(self):
        setor = Setor(nome="Almoxarifado", chefe_responsavel=None)

        with pytest.raises(ValidationError):
            setor.full_clean()

    def test_usuario_pertence_a_unico_setor(self):
        chefe = User.objects.create_user(
            matricula_funcional="12345",
            password="testpass123",
            nome_completo="João Silva",
        )
        setor1 = Setor.objects.create(
            nome="Almoxarifado",
            chefe_responsavel=chefe,
        )

        usuario = User.objects.create_user(
            matricula_funcional="54321",
            password="testpass123",
            nome_completo="Maria Silva",
            setor=setor1,
        )

        assert usuario.setor == setor1
        assert usuario.setor.pk == setor1.pk

    def test_setor_com_usuarios_nao_pode_ser_excluido(self):
        chefe = User.objects.create_user(
            matricula_funcional="12345",
            password="testpass123",
            nome_completo="João Silva",
        )
        setor = Setor.objects.create(
            nome="Almoxarifado",
            chefe_responsavel=chefe,
        )
        chefe.setor = setor
        chefe.save(update_fields=["setor"])
        User.objects.create_user(
            matricula_funcional="54321",
            password="testpass123",
            nome_completo="Maria Silva",
            setor=setor,
        )

        with pytest.raises(ProtectedError):
            setor.delete()
