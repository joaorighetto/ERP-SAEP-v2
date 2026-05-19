from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse
from django.views import View

from apps.requisitions.contexts import build_requisicao_worklist_item
from apps.requisitions.models import StatusRequisicao
from apps.requisitions.policies import queryset_requisicoes_pessoais

_PAGE_SIZE = 20
_PARTIAL_TEMPLATE = "web/pages/requisitions/_list.html"
_FULL_TEMPLATE = "web/pages/requisitions/list.html"

_STATUS_CHOICES = [(s.value, s.label) for s in StatusRequisicao]


class MinhasSolicitacoesView(LoginRequiredMixin, View):
    def get(self, request):
        qs = queryset_requisicoes_pessoais(request.user, skip_prefetch=True).prefetch_related(
            "itens"
        )

        q = request.GET.get("q", "").strip()
        status_filter = request.GET.get("status", "").strip()

        if q:
            qs = qs.filter(Q(numero_publico__icontains=q) | Q(observacao__icontains=q)).distinct()

        if status_filter and status_filter in StatusRequisicao.values:
            qs = qs.filter(status=status_filter)

        qs = qs.order_by("-updated_at")

        paginator = Paginator(qs, _PAGE_SIZE)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        items = [build_requisicao_worklist_item(req, request.user) for req in page_obj]

        is_filtered = bool(q or status_filter)

        ctx = {
            "page_obj": page_obj,
            "items": items,
            "q": q,
            "status_filter": status_filter,
            "status_choices": _STATUS_CHOICES,
            "is_filtered": is_filtered,
            "worklist_url": reverse("web:requisitions_mine"),
        }
        ctx.update(self._nav_context(request))

        if getattr(request, "htmx", False):
            return render(request, _PARTIAL_TEMPLATE, ctx)

        return render(request, _FULL_TEMPLATE, ctx)

    def _nav_context(self, request):
        from apps.web.navigation import get_navigation_context

        return get_navigation_context(request)
