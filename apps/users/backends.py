from django.contrib.auth.backends import ModelBackend

from apps.users.models import User


class MatriculaBackend(ModelBackend):
    """Backend de autenticação que usa matrícula funcional como identificador de login."""

    def authenticate(self, request=None, matricula_funcional=None, password=None, **kwargs):
        if not matricula_funcional or not password:
            return None

        try:
            user = User.objects.get(matricula_funcional=matricula_funcional)
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
