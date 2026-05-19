from django.urls import reverse

from apps.users.models import PapelChoices


def build_navigation_for_user(user):
    """Return navigation allowlist for the given user based on their role."""
    if not user or not user.is_authenticated:
        return []

    papel = getattr(user, "papel", None)

    _solicitante_items = [
        {
            "label": "Solicitações",
            "items": [
                {
                    "label": "Nova solicitação",
                    "url": reverse("web:home"),
                    "icon": "plus-circle",
                    "key": "requisition_create",
                },
                {
                    "label": "Minhas solicitações",
                    "url": reverse("web:requisitions_mine"),
                    "icon": "clipboard-list",
                    "key": "requisitions_mine",
                },
            ],
        },
    ]

    _chefia_items = [
        {
            "label": "Autorizações",
            "items": [
                {
                    "label": "Aprovações pendentes",
                    "url": reverse("web:home"),
                    "icon": "check-circle",
                    "key": "authorizations_list",
                },
                {
                    "label": "Histórico de aprovações",
                    "url": reverse("web:home"),
                    "icon": "clock",
                    "key": "authorizations_history",
                },
            ],
        },
    ]

    _almoxarifado_items = [
        {
            "label": "Solicitações",
            "items": [
                {
                    "label": "Minhas solicitações",
                    "url": reverse("web:requisitions_mine"),
                    "icon": "clipboard-list",
                    "key": "requisitions_mine",
                },
            ],
        },
        {
            "label": "Almoxarifado",
            "items": [
                {
                    "label": "Fila de atendimento",
                    "url": reverse("web:home"),
                    "icon": "inbox",
                    "key": "fulfillments_list",
                },
                {
                    "label": "Estoque",
                    "url": reverse("web:home"),
                    "icon": "archive-box",
                    "key": "stock_list",
                },
                {
                    "label": "Materiais",
                    "url": reverse("web:home"),
                    "icon": "cube",
                    "key": "materials_list",
                },
            ],
        },
    ]

    nav_by_papel = {
        PapelChoices.SOLICITANTE: _solicitante_items,
        PapelChoices.AUXILIAR_SETOR: _solicitante_items,
        PapelChoices.CHEFE_SETOR: _chefia_items,
        PapelChoices.AUXILIAR_ALMOXARIFADO: _almoxarifado_items,
        PapelChoices.CHEFE_ALMOXARIFADO: _almoxarifado_items,
    }

    return nav_by_papel.get(papel, [])


def get_active_key(request):
    """Resolve the active navigation key based on current URL."""
    resolver_match = getattr(request, "resolver_match", None)
    if not resolver_match:
        return None
    return resolver_match.url_name


def get_navigation_context(request):
    """Return context dict with navigation and active key for templates."""
    navigation = build_navigation_for_user(request.user)
    active_key = get_active_key(request)
    return {
        "navigation": navigation,
        "nav_active_key": active_key,
    }
