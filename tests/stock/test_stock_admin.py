import pytest
from django.contrib import admin
from django.test import RequestFactory

from apps.stock.admin import EstoqueMaterialAdmin
from apps.stock.models import EstoqueMaterial
from apps.users.models import User


@pytest.mark.django_db
class TestStockAdmin:
    @staticmethod
    def _staff_request():
        request = RequestFactory().get("/admin/")
        request.user = User.objects.create_superuser(
            matricula_funcional="99011",
            password="testpass123",
            nome_completo="Super Admin Stock",
        )
        return request

    def test_estoque_material_admin_bloqueia_mutacao_manual(self):
        request = self._staff_request()
        model_admin = EstoqueMaterialAdmin(EstoqueMaterial, admin.site)

        assert model_admin.has_view_permission(request) is True
        assert model_admin.has_add_permission(request) is False
        assert model_admin.has_change_permission(request) is False
        assert model_admin.has_delete_permission(request) is False
        assert model_admin.get_readonly_fields(request) == (
            "material",
            "saldo_fisico",
            "saldo_reservado",
            "saldo_disponivel",
            "created_at",
            "updated_at",
        )
