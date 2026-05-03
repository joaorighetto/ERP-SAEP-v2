"""Smoke tests for DRF/OpenAPI configuration."""

import json

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.models import Setor, User


@pytest.mark.django_db
class TestOpenAPISchema:
    """Test OpenAPI schema generation and accessibility."""

    @staticmethod
    def _criar_staff():
        usuario = User.objects.create(
            matricula_funcional="990001",
            nome_completo="Staff Schema",
            is_active=True,
            is_staff=True,
        )
        setor = Setor.objects.create(nome="Tecnologia", chefe_responsavel=usuario)
        usuario.setor = setor
        usuario.save()
        return usuario

    @staticmethod
    def _criar_usuario_nao_staff():
        usuario = User.objects.create(
            matricula_funcional="990002",
            nome_completo="Usuario Schema",
            is_active=True,
            is_staff=False,
        )
        setor = Setor.objects.create(nome="Operacao", chefe_responsavel=usuario)
        usuario.setor = setor
        usuario.save()
        return usuario

    @staticmethod
    def _schema_json(response):
        return json.loads(response.content.decode())

    def _get_schema(self):
        usuario = self._criar_staff()
        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("schema"), HTTP_ACCEPT="application/vnd.oai.openapi+json")
        assert response.status_code == 200
        return self._schema_json(response)

    @override_settings(DEBUG=False)
    def test_schema_endpoint_requires_staff(self):
        """Verify /api/v1/schema/ requires staff outside DEBUG override."""
        client = APIClient()
        response = client.get(reverse("schema"))
        assert response.status_code == 403

    @override_settings(DEBUG=False)
    def test_schema_endpoint_non_staff_is_denied(self):
        """Verify authenticated non-staff users cannot access /api/v1/schema/."""
        usuario = self._criar_usuario_nao_staff()
        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("schema"), HTTP_ACCEPT="application/vnd.oai.openapi+json")
        assert response.status_code == 403

    def test_schema_endpoint_staff_can_access(self):
        """Verify staff users can access /api/v1/schema/."""
        usuario = self._criar_staff()
        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("schema"), HTTP_ACCEPT="application/vnd.oai.openapi+json")
        assert response.status_code == 200

    @override_settings(DEBUG=False)
    def test_swagger_ui_requires_staff(self):
        """Verify Swagger UI endpoint requires staff outside DEBUG override."""
        client = APIClient()
        response = client.get(reverse("swagger-ui"))
        assert response.status_code == 403

    @override_settings(DEBUG=False)
    def test_swagger_ui_non_staff_is_denied(self):
        """Verify authenticated non-staff users cannot access Swagger UI."""
        usuario = self._criar_usuario_nao_staff()
        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("swagger-ui"))
        assert response.status_code == 403

    def test_swagger_ui_returns_html_for_staff(self):
        """Verify Swagger UI returns HTML content for staff users."""
        usuario = self._criar_staff()
        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("swagger-ui"))
        assert response.status_code == 200
        assert b"<!DOCTYPE html>" in response.content or b"<!DOCTYPE" in response.content

    def test_drf_is_properly_configured(self):
        """Verify DRF is properly configured with custom pagination."""
        from django.conf import settings

        assert "DEFAULT_PAGINATION_CLASS" in settings.REST_FRAMEWORK
        assert (
            settings.REST_FRAMEWORK["DEFAULT_PAGINATION_CLASS"]
            == "apps.core.api.pagination.StandardPagination"
        )

    def test_exception_handler_is_configured(self):
        """Verify custom exception handler is configured."""
        from django.conf import settings

        assert "EXCEPTION_HANDLER" in settings.REST_FRAMEWORK
        assert (
            settings.REST_FRAMEWORK["EXCEPTION_HANDLER"]
            == "apps.core.api.exceptions.api_exception_handler"
        )

    def test_core_app_is_installed(self):
        """Verify apps.core is in INSTALLED_APPS."""
        from django.conf import settings

        assert "apps.core" in settings.INSTALLED_APPS

    def test_schema_contem_rotas_de_requisicoes(self):
        """Verify requisitions routes are exposed in OpenAPI."""
        schema = self._get_schema()
        paths = schema["paths"]

        assert "/api/v1/auth/csrf/" in paths
        assert "/api/v1/auth/login/" in paths
        assert "/api/v1/auth/logout/" in paths
        assert "/api/v1/auth/me/" in paths
        assert "/api/v1/materials/{id}/" in paths
        assert "/api/v1/requisitions/" in paths
        assert "/api/v1/requisitions/{id}/submit/" in paths
        assert "/api/v1/requisitions/{id}/return-to-draft/" in paths
        assert "/api/v1/requisitions/{id}/discard/" in paths
        assert "/api/v1/requisitions/{id}/cancel/" in paths
        assert "/api/v1/requisitions/{id}/authorize/" in paths
        assert "/api/v1/requisitions/{id}/refuse/" in paths
        assert "/api/v1/requisitions/{id}/fulfill/" in paths
        assert "/api/v1/requisitions/pending-approvals/" in paths
        assert "/api/v1/requisitions/pending-fulfillments/" in paths
        assert paths["/api/v1/materials/{id}/"]["get"]["operationId"] == "materials_retrieve"

        components = schema["components"]["schemas"]
        assert "RequisicaoItemFulfillInput" in components
        item_schema = components["RequisicaoItemFulfillInput"]["properties"]
        assert "quantidade_entregue" in item_schema
        assert "justificativa_atendimento_parcial" in item_schema

    def test_auth_endpoints_declaram_requests_responses_e_status_esperados(self):
        """Verify auth endpoints expose explicit schema contracts."""
        schema = self._get_schema()
        paths = schema["paths"]

        expected_operations = {
            ("/api/v1/auth/csrf/", "get"): {
                "request_body": False,
                "success_codes": {"200"},
                "success_ref": "#/components/schemas/CsrfTokenOutput",
                "error_codes": set(),
            },
            ("/api/v1/auth/login/", "post"): {
                "request_body": True,
                "request_ref": "#/components/schemas/AuthLoginInput",
                "success_codes": {"200"},
                "success_ref": "#/components/schemas/AuthSessionOutput",
                "error_codes": {"401", "403"},
            },
            ("/api/v1/auth/logout/", "post"): {
                "request_body": False,
                "success_codes": {"204"},
                "success_ref": None,
                "error_codes": {"403"},
            },
            ("/api/v1/auth/me/", "get"): {
                "request_body": False,
                "success_codes": {"200"},
                "success_ref": "#/components/schemas/AuthSessionOutput",
                "error_codes": {"401"},
            },
        }

        error_ref = "#/components/schemas/ErrorResponse"

        for (path, method), expectation in expected_operations.items():
            operation = paths[path][method]
            responses = operation["responses"]

            if expectation["request_body"]:
                assert "requestBody" in operation
                assert (
                    operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
                    == expectation["request_ref"]
                )
            else:
                assert "requestBody" not in operation

            for code in expectation["success_codes"]:
                assert code in responses
                if expectation["success_ref"] is None:
                    assert "content" not in responses[code]
                else:
                    assert (
                        responses[code]["content"]["application/json"]["schema"]["$ref"]
                        == expectation["success_ref"]
                    )

            for code in expectation["error_codes"]:
                assert code in responses
                assert responses[code]["content"]["application/json"]["schema"]["$ref"] == error_ref

    def test_error_response_schema_declara_trace_id(self):
        """Verify the standard error envelope includes trace_id in OpenAPI."""
        schema = self._get_schema()
        error_detail = schema["components"]["schemas"]["ErrorDetail"]

        assert "trace_id" in error_detail["properties"]
        assert error_detail["properties"]["trace_id"]["type"] == "string"
        assert "trace_id" not in error_detail.get("required", [])

    def test_requisicao_actions_declaram_requests_and_responses_esperados(self):
        """Verify requisition actions expose explicit schema contracts."""
        schema = self._get_schema()
        paths = schema["paths"]

        expected_operations = {
            ("/api/v1/requisitions/", "post"): {
                "request_body": True,
                "request_ref": "#/components/schemas/RequisicaoCreateInput",
                "success_codes": {"201"},
                "success_ref": "#/components/schemas/RequisicaoDetailOutput",
                "error_codes": {"400", "403", "404", "409"},
            },
            ("/api/v1/requisitions/{id}/submit/", "post"): {
                "request_body": False,
                "success_codes": {"200"},
                "success_ref": "#/components/schemas/RequisicaoDetailOutput",
                "error_codes": {"403", "404", "409"},
            },
            ("/api/v1/requisitions/{id}/return-to-draft/", "post"): {
                "request_body": False,
                "success_codes": {"200"},
                "success_ref": "#/components/schemas/RequisicaoDetailOutput",
                "error_codes": {"403", "404", "409"},
            },
            ("/api/v1/requisitions/{id}/discard/", "delete"): {
                "request_body": False,
                "success_codes": {"204"},
                "success_ref": None,
                "error_codes": {"403", "404", "409"},
            },
            ("/api/v1/requisitions/{id}/cancel/", "post"): {
                "request_body": True,
                "request_ref": "#/components/schemas/RequisicaoCancelInput",
                "success_codes": {"200"},
                "success_ref": "#/components/schemas/RequisicaoDetailOutput",
                "error_codes": {"400", "403", "404", "409"},
            },
            ("/api/v1/requisitions/{id}/authorize/", "post"): {
                "request_body": True,
                "request_ref": "#/components/schemas/RequisicaoAuthorizeInput",
                "success_codes": {"200"},
                "success_ref": "#/components/schemas/RequisicaoDetailOutput",
                "error_codes": {"400", "403", "404", "409"},
            },
            ("/api/v1/requisitions/{id}/refuse/", "post"): {
                "request_body": True,
                "request_ref": "#/components/schemas/RequisicaoRefuseInput",
                "success_codes": {"200"},
                "success_ref": "#/components/schemas/RequisicaoDetailOutput",
                "error_codes": {"400", "403", "404", "409"},
            },
            ("/api/v1/requisitions/{id}/fulfill/", "post"): {
                "request_body": True,
                "request_ref": "#/components/schemas/RequisicaoFulfillInput",
                "success_codes": {"200"},
                "success_ref": "#/components/schemas/RequisicaoDetailOutput",
                "error_codes": {"400", "403", "404", "409"},
            },
            ("/api/v1/requisitions/pending-approvals/", "get"): {
                "request_body": False,
                "success_codes": {"200"},
                "success_ref": "#/components/schemas/RequisicaoPendingApprovalPaginated",
                "error_codes": {"403"},
            },
            ("/api/v1/requisitions/pending-fulfillments/", "get"): {
                "request_body": False,
                "success_codes": {"200"},
                "success_ref": "#/components/schemas/RequisicaoPendingFulfillmentPaginated",
                "error_codes": {"403"},
            },
        }

        error_ref = "#/components/schemas/ErrorResponse"

        for (path, method), expectation in expected_operations.items():
            operation = paths[path][method]
            responses = operation["responses"]

            if expectation["request_body"]:
                assert "requestBody" in operation
                assert (
                    operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
                    == expectation["request_ref"]
                )
            else:
                assert "requestBody" not in operation

            for code in expectation["success_codes"]:
                assert code in responses
                if expectation["success_ref"] is None:
                    assert "content" not in responses[code]
                else:
                    assert (
                        responses[code]["content"]["application/json"]["schema"]["$ref"]
                        == expectation["success_ref"]
                    )

            for code in expectation["error_codes"]:
                assert code in responses
                assert responses[code]["content"]["application/json"]["schema"]["$ref"] == error_ref
