import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError

from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial


@pytest.mark.django_db
class TestMaterial:
    @staticmethod
    def _criar_subgrupo():
        grupo = GrupoMaterial.objects.create(codigo_grupo="013", nome="Material Hidráulico")
        return SubgrupoMaterial.objects.create(
            grupo=grupo,
            codigo_subgrupo="024",
            nome="Tubos e Conexões",
        )

    def test_criar_material_com_campos_validos(self):
        subgrupo = self._criar_subgrupo()
        material = Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo="013.024.001",
            nome="Tubo PVC 25mm",
            descricao="Tubo para rede de água",
            unidade_medida="UN",
            sequencial="001",
            observacoes_internas="Uso recorrente",
        )

        assert material.subgrupo == subgrupo
        assert material.codigo_completo == "013.024.001"
        assert material.is_active is True
        assert material.created_at is not None
        assert material.updated_at is not None

    def test_codigo_completo_deve_ser_unico(self):
        subgrupo = self._criar_subgrupo()
        Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo="013.024.001",
            nome="Item 1",
            unidade_medida="UN",
            sequencial="001",
        )

        with pytest.raises(IntegrityError):
            Material.objects.create(
                subgrupo=subgrupo,
                codigo_completo="013.024.001",
                nome="Item 2",
                unidade_medida="UN",
                sequencial="002",
            )

    @pytest.mark.parametrize("codigo_invalido", ["13.024.001", "013.24.001", "013024001", "ABC"])
    def test_codigo_completo_deve_seguir_padrao(self, codigo_invalido):
        subgrupo = self._criar_subgrupo()
        material = Material(
            subgrupo=subgrupo,
            codigo_completo=codigo_invalido,
            nome="Item",
            unidade_medida="UN",
            sequencial="001",
        )

        with pytest.raises(ValidationError):
            material.full_clean()

    def test_material_sem_subgrupo_nao_permitido(self):
        with pytest.raises(IntegrityError):
            Material.objects.create(
                subgrupo=None,
                codigo_completo="013.024.001",
                nome="Item sem subgrupo",
                unidade_medida="UN",
                sequencial="001",
            )

    def test_deletar_subgrupo_com_material_vinculado_levanta_protected_error(self):
        subgrupo = self._criar_subgrupo()
        Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo="013.024.001",
            nome="Item",
            unidade_medida="UN",
            sequencial="001",
        )

        with pytest.raises(ProtectedError):
            subgrupo.delete()

    def test_ordering_por_codigo_completo(self):
        subgrupo = self._criar_subgrupo()
        Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo="013.024.003",
            nome="C",
            unidade_medida="UN",
            sequencial="003",
        )
        Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo="013.024.001",
            nome="A",
            unidade_medida="UN",
            sequencial="001",
        )
        Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo="013.024.002",
            nome="B",
            unidade_medida="UN",
            sequencial="002",
        )

        materiais = list(Material.objects.all())
        assert [m.codigo_completo for m in materiais] == [
            "013.024.001",
            "013.024.002",
            "013.024.003",
        ]

    def test_related_name_materiais_no_subgrupo(self):
        subgrupo = self._criar_subgrupo()
        material = Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo="013.024.001",
            nome="A",
            unidade_medida="UN",
            sequencial="001",
        )
        assert subgrupo.materiais.get() == material

    def test_permite_inativacao_de_material(self):
        subgrupo = self._criar_subgrupo()
        material = Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo="013.024.001",
            nome="A",
            unidade_medida="UN",
            sequencial="001",
            is_active=True,
        )

        material.is_active = False
        material.save(update_fields=["is_active"])
        material.refresh_from_db()

        assert material.is_active is False
