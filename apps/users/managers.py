from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    def create_user(self, matricula_funcional, password=None, **extra_fields):
        if not matricula_funcional:
            raise ValueError("Matrícula funcional é obrigatória.")
        user = self.model(matricula_funcional=matricula_funcional, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, matricula_funcional, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(matricula_funcional, password, **extra_fields)
