from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class MatriculaBackend(ModelBackend):
    """Backend de autenticação que usa matrícula funcional como identificador de login."""

    def authenticate(self, request=None, username=None, password=None, **kwargs):
        if password is None:
            return None

        user_model = get_user_model()
        matricula_funcional = username or kwargs.get(user_model.USERNAME_FIELD)
        if not matricula_funcional:
            return None

        try:
            user = user_model._default_manager.get(matricula_funcional=matricula_funcional)
        except user_model.DoesNotExist:
            user_model().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None

    def get_user(self, user_id):
        user_model = get_user_model()
        try:
            return user_model._default_manager.get(pk=user_id)
        except user_model.DoesNotExist:
            return None
