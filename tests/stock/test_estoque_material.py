from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.db.models import ProtectedError

from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.stock.models import EstoqueMaterial


@pytest.mark.django_db
class TestEstoqueMaterial:
    @staticmethod
    def _criar_material(codigo_completo="013.024.001", sequencial="001"):
        grupo, _ = GrupoMaterial.objects.get_or_create(
            codigo_grupo="013",
            defaults={"nome": "Material Hidráulico"},
        )
        subgrupo, _ = SubgrupoMaterial.objects.get_or_create(
            grupo=grupo,
            codigo_subgrupo="024",
            defaults={"nome": "Tubos e Conexões"},
        )
        return Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo=codigo_completo,
            nome=f"Material {sequencial}",
            unidade_medida="UN",
            sequencial=sequencial,
        )

    def test_criar_estoque_com_campos_validos(self):
        material = self._criar_material()
        estoque = EstoqueMaterial.objects.create(
            material=material,
            saldo_fisico=Decimal("10.500"),
            saldo_reservado=Decimal("3.250"),
        )

        assert estoque.material == material
        assert estoque.saldo_fisico == Decimal("10.500")
        assert estoque.saldo_reservado == Decimal("3.250")

    def test_str_representation(self):
        material = self._criar_material()
        estoque = EstoqueMaterial.objects.create(
            material=material,
            saldo_fisico=Decimal("10.000"),
            saldo_reservado=Decimal("2.000"),
        )
        assert str(estoque) == "013.024.001 — disponível: 8.000"

    def test_saldo_disponivel_calculo_normal(self):
        material = self._criar_material()
        estoque = EstoqueMaterial.objects.create(
            material=material,
            saldo_fisico=Decimal("10.000"),
            saldo_reservado=Decimal("2.500"),
        )
        assert estoque.saldo_disponivel == Decimal("7.500")

    def test_saldo_disponivel_calculo_zero(self):
        material = self._criar_material()
        estoque = EstoqueMaterial.objects.create(
            material=material,
            saldo_fisico=Decimal("2.000"),
            saldo_reservado=Decimal("2.000"),
        )
        assert estoque.saldo_disponivel == Decimal("0.000")

    def test_saldo_disponivel_pode_ser_negativo_em_divergencia(self):
        material = self._criar_material()
        estoque = EstoqueMaterial.objects.create(
            material=material,
            saldo_fisico=Decimal("1.000"),
            saldo_reservado=Decimal("2.500"),
        )
        assert estoque.saldo_disponivel == Decimal("-1.500")

    def test_saldo_fisico_nao_pode_ser_negativo(self):
        material = self._criar_material()
        with pytest.raises(IntegrityError):
            EstoqueMaterial.objects.create(
                material=material,
                saldo_fisico=Decimal("-0.001"),
                saldo_reservado=Decimal("0.000"),
            )

    def test_saldo_reservado_nao_pode_ser_negativo(self):
        material = self._criar_material()
        with pytest.raises(IntegrityError):
            EstoqueMaterial.objects.create(
                material=material,
                saldo_fisico=Decimal("1.000"),
                saldo_reservado=Decimal("-0.001"),
            )

    def test_material_tem_relacao_reversa_estoque(self):
        material = self._criar_material()
        estoque = EstoqueMaterial.objects.create(material=material)
        assert material.estoque == estoque

    def test_deletar_material_com_estoque_levanta_protected_error(self):
        material = self._criar_material()
        EstoqueMaterial.objects.create(material=material)
        with pytest.raises(ProtectedError):
            material.delete()

    def test_ordering_por_codigo_material(self):
        material_b = self._criar_material(codigo_completo="013.024.002", sequencial="002")
        material_a = self._criar_material(codigo_completo="013.024.001", sequencial="001")
        material_c = self._criar_material(codigo_completo="013.024.003", sequencial="003")

        EstoqueMaterial.objects.create(material=material_b)
        EstoqueMaterial.objects.create(material=material_a)
        EstoqueMaterial.objects.create(material=material_c)

        estoques = list(EstoqueMaterial.objects.all())
        assert [e.material.codigo_completo for e in estoques] == [
            "013.024.001",
            "013.024.002",
            "013.024.003",
        ]
