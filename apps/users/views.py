from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api.serializers import ErrorResponseSerializer
from apps.users.authentication import SessionAuthentication401
from apps.users.serializers import (
    AuthLoginInputSerializer,
    AuthSessionOutputSerializer,
    CsrfTokenOutputSerializer,
)


def _session_payload(user):
    return {
        "id": user.id,
        "matricula_funcional": user.matricula_funcional,
        "nome_completo": user.nome_completo,
        "papel": user.papel,
        "setor": user.setor,
        "is_authenticated": user.is_authenticated,
    }


def _enforce_csrf(request):
    SessionAuthentication().enforce_csrf(request)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class AuthCsrfView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="auth_csrf",
        tags=["auth"],
        responses={200: CsrfTokenOutputSerializer()},
    )
    def get(self, request):
        return Response({"csrf_token": get_token(request)})


class AuthLoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="auth_login",
        tags=["auth"],
        request=AuthLoginInputSerializer,
        responses={
            200: AuthSessionOutputSerializer(),
            401: ErrorResponseSerializer(),
            403: ErrorResponseSerializer(),
        },
    )
    def post(self, request):
        _enforce_csrf(request)
        serializer = AuthLoginInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request=request,
            username=serializer.validated_data["matricula_funcional"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response(
                {
                    "error": {
                        "code": "authentication_failed",
                        "message": "Matrícula funcional ou senha inválidas.",
                        "details": None,
                        "trace_id": request.META.get("HTTP_X_TRACE_ID"),
                    }
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        login(request, user)
        return Response(AuthSessionOutputSerializer(_session_payload(user)).data)


class AuthLogoutView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="auth_logout",
        tags=["auth"],
        request=None,
        responses={
            204: None,
            403: ErrorResponseSerializer(),
        },
    )
    def post(self, request):
        _enforce_csrf(request)
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuthMeView(APIView):
    authentication_classes = [SessionAuthentication401]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="auth_me",
        tags=["auth"],
        responses={
            200: AuthSessionOutputSerializer(),
            401: ErrorResponseSerializer(),
        },
    )
    def get(self, request):
        serializer = AuthSessionOutputSerializer(_session_payload(request.user))
        return Response(serializer.data)
