from rest_framework import serializers


class AuthSetorOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    nome = serializers.CharField(read_only=True)


class AuthSessionOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    matricula_funcional = serializers.CharField(read_only=True)
    nome_completo = serializers.CharField(read_only=True)
    papel = serializers.CharField(read_only=True)
    setor = AuthSetorOutputSerializer(read_only=True, allow_null=True)
    is_authenticated = serializers.BooleanField(read_only=True)


class CsrfTokenOutputSerializer(serializers.Serializer):
    csrf_token = serializers.CharField(read_only=True)


class AuthLoginInputSerializer(serializers.Serializer):
    matricula_funcional = serializers.CharField()
    password = serializers.CharField(write_only=True)
