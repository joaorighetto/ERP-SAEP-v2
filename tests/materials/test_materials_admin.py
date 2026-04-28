import pytest
from django.contrib import admin
from django.test import RequestFactory

from apps.materials.admin import GrupoMaterialAdmin, MaterialAdmin, SubgrupoMaterialAdmin
from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.users.models import User


@pytest.mark.django_db
class TestMaterialsAdmin:
    @staticmethod
    def _staff_request():
        request = RequestFactory().get("/admin/")
        request.user = User.objects.create_superuser(
            matricula_funcional="99010",
            password="testpass123",
            nome_completo="Super Admin Materials",
        )
        return request

    def test_grupo_material_admin_bloqueia_mutacao_manual_de_dados_scpi(self):
        request = self._staff_request()
        model_admin = GrupoMaterialAdmin(GrupoMaterial, admin.site)

        assert model_admin.has_view_permission(request) is True
        assert model_admin.has_add_permission(request) is False
        assert model_admin.has_change_permission(request) is False
        assert model_admin.has_delete_permission(request) is False
        assert model_admin.get_readonly_fields(request) == (
            "codigo_grupo",
            "nome",
            "created_at",
            "updated_at",
        )

    def test_subgrupo_material_admin_bloqueia_mutacao_manual_de_dados_scpi(self):
        request = self._staff_request()
        model_admin = SubgrupoMaterialAdmin(SubgrupoMaterial, admin.site)

        assert model_admin.has_view_permission(request) is True
        assert model_admin.has_add_permission(request) is False
        assert model_admin.has_change_permission(request) is False
        assert model_admin.has_delete_permission(request) is False
        assert model_admin.get_readonly_fields(request) == (
            "grupo",
            "codigo_subgrupo",
            "nome",
            "created_at",
            "updated_at",
        )

    def test_material_admin_bloqueia_mutacao_manual_de_dados_scpi(self):
        request = self._staff_request()
        model_admin = MaterialAdmin(Material, admin.site)

        assert model_admin.has_view_permission(request) is True
        assert model_admin.has_add_permission(request) is False
        assert model_admin.has_change_permission(request) is False
        assert model_admin.has_delete_permission(request) is False
        assert model_admin.get_readonly_fields(request) == (
            "subgrupo",
            "codigo_completo",
            "nome",
            "descricao",
            "unidade_medida",
            "sequencial",
            "is_active",
            "observacoes_internas",
            "created_at",
            "updated_at",
        )
