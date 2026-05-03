from django.urls import path

from apps.users.views import AuthCsrfView, AuthLoginView, AuthLogoutView, AuthMeView

urlpatterns = [
    path("auth/csrf/", AuthCsrfView.as_view(), name="auth-csrf"),
    path("auth/login/", AuthLoginView.as_view(), name="auth-login"),
    path("auth/logout/", AuthLogoutView.as_view(), name="auth-logout"),
    path("auth/me/", AuthMeView.as_view(), name="auth-me"),
]
