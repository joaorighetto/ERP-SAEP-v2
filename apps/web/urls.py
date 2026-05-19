from django.urls import path

from apps.web.views import auth as auth_views
from apps.web.views import home as home_views
from apps.web.views import requisitions as requisitions_views

app_name = "web"

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("logout/concluido/", auth_views.LoggedOutView.as_view(), name="logged_out"),
    path("", home_views.HomeView.as_view(), name="home"),
    path(
        "minhas-solicitacoes/",
        requisitions_views.MinhasSolicitacoesView.as_view(),
        name="requisitions_mine",
    ),
]
