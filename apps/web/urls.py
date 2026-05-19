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
    # Issue #40 — nova solicitação
    path(
        "requisicoes/nova/",
        requisitions_views.RequisicaoCreateView.as_view(),
        name="requisition_create",
    ),
    path(
        "requisicoes/<int:pk>/editar/",
        requisitions_views.RequisicaoEditView.as_view(),
        name="requisition_edit",
    ),
    path(
        "requisicoes/<int:pk>/enviar/",
        requisitions_views.requisition_send_view,
        name="requisition_send",
    ),
    path(
        "requisicoes/materiais/buscar/",
        requisitions_views.material_search_view,
        name="material_search",
    ),
    path(
        "requisicoes/item/adicionar/",
        requisitions_views.requisition_item_add_view,
        name="requisition_item_add",
    ),
    path(
        "requisicoes/beneficiarios/buscar/",
        requisitions_views.beneficiary_search_view,
        name="beneficiary_search",
    ),
]
