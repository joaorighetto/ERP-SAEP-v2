from django.urls import path

from apps.web.views import home as home_views
from apps.web.views import requisitions as requisitions_views

app_name = "web"

urlpatterns = [
    path("", home_views.HomeView.as_view(), name="home"),
    path(
        "minhas-solicitacoes/",
        requisitions_views.MinhasSolicitacoesView.as_view(),
        name="requisitions_mine",
    ),
]
