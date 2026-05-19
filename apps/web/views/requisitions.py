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


# ---------------------------------------------------------------------------
# Nova solicitação / Edição de rascunho
# ---------------------------------------------------------------------------

_FORM_FULL_TEMPLATE = "web/pages/requisitions/form.html"
_FORM_PARTIAL_TEMPLATE = "web/pages/requisitions/_form_body.html"
_ITEM_ROW_TEMPLATE = "web/pages/requisitions/_item_row.html"
_MATERIAL_RESULTS_TEMPLATE = "web/pages/requisitions/_material_results.html"
_BENEFICIARY_RESULTS_TEMPLATE = "web/pages/requisitions/_beneficiary_results.html"


def _nav_context(request):
    from apps.web.navigation import get_navigation_context

    return get_navigation_context(request)


def _build_itens_from_formset(item_formset) -> list:
    """Extrai itens válidos (não deletados, não vazios) do formset.

    Retorna lista de ItemRascunhoData. Não valida domínio.
    """
    from decimal import Decimal

    from apps.requisitions.domain.types import ItemRascunhoData

    itens = []
    for form in item_formset:
        if not form.is_valid():
            continue
        data = form.cleaned_data
        if data.get("DELETE"):
            continue
        material_id = data.get("material_id")
        quantidade = data.get("quantidade_solicitada")
        if not material_id or not quantidade:
            continue
        itens.append(
            ItemRascunhoData(
                material_id=material_id,
                quantidade_solicitada=Decimal(str(quantidade)),
                observacao=data.get("observacao") or "",
            )
        )
    return itens


def _material_nomes_para_itens(itens_qs) -> dict:
    """Retorna {material_id: nome} para pré-preencher display no template de edição."""
    return {item.material_id: item.material.nome for item in itens_qs}


def _is_solicitante_simples(user) -> bool:
    from apps.users.models import PapelChoices

    return getattr(user, "papel", None) == PapelChoices.SOLICITANTE


class RequisicaoCreateView(LoginRequiredMixin, View):
    """Criar nova requisição (rascunho)."""

    def get(self, request):
        from apps.requisitions.forms import ItemRequisicaoFormSet, RequisicaoRascunhoForm

        is_solicitante = _is_solicitante_simples(request.user)
        initial_beneficiario = request.user.pk if is_solicitante else None

        header_form = RequisicaoRascunhoForm(initial={"beneficiario_id": initial_beneficiario})
        item_formset = ItemRequisicaoFormSet(prefix="form", initial=[{}])

        ctx = {
            "header_form": header_form,
            "item_formset": item_formset,
            "is_solicitante": is_solicitante,
            "beneficiario_display": request.user.nome_completo if is_solicitante else "",
            "material_nomes": {},
            "page_title": "Nova solicitação",
            "form_action": reverse("web:requisition_create"),
            "acao_enviar_label": "Enviar para autorização",
        }
        ctx.update(_nav_context(request))
        return render(request, _FORM_FULL_TEMPLATE, ctx)

    def post(self, request):
        from apps.requisitions.forms import ItemRequisicaoFormSet, RequisicaoRascunhoForm
        from apps.requisitions.services import criar_rascunho_requisicao, enviar_para_autorizacao
        from apps.users.models import User

        is_solicitante = _is_solicitante_simples(request.user)

        header_form = RequisicaoRascunhoForm(data=request.POST)
        item_formset = ItemRequisicaoFormSet(data=request.POST, prefix="form")

        header_valid = header_form.is_valid()
        formset_valid = item_formset.is_valid()

        if not header_valid or not formset_valid:
            return self._render_422(request, header_form, item_formset, is_solicitante)

        itens = _build_itens_from_formset(item_formset)
        if not itens:
            header_form.add_error(None, "Informe ao menos um item para criar a requisição.")
            return self._render_422(request, header_form, item_formset, is_solicitante)

        try:
            beneficiario_id = header_form.cleaned_data["beneficiario_id"]
            # PER-01: force self for solicitante regardless of posted value
            if is_solicitante:
                beneficiario_id = request.user.pk
            beneficiario = User.objects.get(pk=beneficiario_id, is_active=True)
        except User.DoesNotExist:
            header_form.add_error("beneficiario_id", "Beneficiário inválido.")
            return self._render_422(request, header_form, item_formset, is_solicitante)

        try:
            requisicao = criar_rascunho_requisicao(
                criador=request.user,
                beneficiario=beneficiario,
                observacao=header_form.cleaned_data.get("observacao") or "",
                itens=itens,
            )
        except Exception as exc:
            header_form.add_error(None, str(exc))
            return self._render_422(request, header_form, item_formset, is_solicitante)

        acao = request.POST.get("acao", "salvar")
        if acao == "enviar":
            try:
                enviar_para_autorizacao(requisicao=requisicao, ator=request.user)
            except Exception as exc:
                header_form.add_error(None, str(exc))
                return self._render_422(request, header_form, item_formset, is_solicitante)

        if getattr(request, "htmx", False):
            from django_htmx.http import HttpResponseClientRedirect

            return HttpResponseClientRedirect(reverse("web:requisitions_mine"))

        from django.shortcuts import redirect

        return redirect("web:requisitions_mine")

    def _render_422(self, request, header_form, item_formset, is_solicitante):
        ctx = {
            "header_form": header_form,
            "item_formset": item_formset,
            "is_solicitante": is_solicitante,
            "beneficiario_display": request.user.nome_completo if is_solicitante else "",
            "material_nomes": {},
            "page_title": "Nova solicitação",
            "form_action": reverse("web:requisition_create"),
            "acao_enviar_label": "Enviar para autorização",
        }
        ctx.update(_nav_context(request))
        if getattr(request, "htmx", False):
            return render(request, _FORM_PARTIAL_TEMPLATE, ctx, status=422)
        return render(request, _FORM_FULL_TEMPLATE, ctx, status=422)


class RequisicaoEditView(LoginRequiredMixin, View):
    """Editar rascunho de requisição existente."""

    def _load_rascunho(self, request, pk):
        from django.http import Http404

        from apps.requisitions.models import Requisicao, StatusRequisicao
        from apps.requisitions.policies import (
            pode_manipular_pre_autorizacao,
            pode_visualizar_requisicao,
        )

        try:
            req = (
                Requisicao.objects.select_related("criador", "beneficiario", "setor_beneficiario")
                .prefetch_related("itens__material")
                .get(pk=pk)
            )
        except Requisicao.DoesNotExist:
            raise Http404

        if not pode_visualizar_requisicao(request.user, req):
            raise Http404

        if not pode_manipular_pre_autorizacao(request.user, req):
            raise Http404

        if req.status != StatusRequisicao.RASCUNHO:
            raise Http404

        return req

    def get(self, request, pk):
        from apps.requisitions.forms import ItemRequisicaoFormSet, RequisicaoRascunhoForm

        req = self._load_rascunho(request, pk)
        is_solicitante = _is_solicitante_simples(request.user)

        header_form = RequisicaoRascunhoForm(
            initial={
                "beneficiario_id": req.beneficiario_id,
                "observacao": req.observacao,
            }
        )

        itens_list = list(req.itens.all())
        material_nomes = _material_nomes_para_itens(itens_list)

        item_initial = [
            {
                "material_id": item.material_id,
                "quantidade_solicitada": item.quantidade_solicitada,
                "observacao": item.observacao,
                "material_nome": item.material.nome,
            }
            for item in itens_list
        ]
        item_formset = ItemRequisicaoFormSet(prefix="form", initial=item_initial)

        ctx = {
            "header_form": header_form,
            "item_formset": item_formset,
            "is_solicitante": is_solicitante,
            "beneficiario_display": req.beneficiario.nome_completo,
            "material_nomes": material_nomes,
            "page_title": "Editar rascunho",
            "form_action": reverse("web:requisition_edit", args=[pk]),
            "acao_enviar_label": "Enviar para autorização",
            "requisicao": req,
        }
        ctx.update(_nav_context(request))
        return render(request, _FORM_FULL_TEMPLATE, ctx)

    def post(self, request, pk):
        from apps.requisitions.forms import ItemRequisicaoFormSet, RequisicaoRascunhoForm
        from apps.requisitions.services import (
            atualizar_rascunho_requisicao,
            enviar_para_autorizacao,
        )

        req = self._load_rascunho(request, pk)
        is_solicitante = _is_solicitante_simples(request.user)

        header_form = RequisicaoRascunhoForm(data=request.POST)
        item_formset = ItemRequisicaoFormSet(data=request.POST, prefix="form")

        header_valid = header_form.is_valid()
        formset_valid = item_formset.is_valid()

        if not header_valid or not formset_valid:
            return self._render_422(request, pk, req, header_form, item_formset, is_solicitante)

        itens = _build_itens_from_formset(item_formset)
        if not itens:
            header_form.add_error(None, "Informe ao menos um item.")
            return self._render_422(request, pk, req, header_form, item_formset, is_solicitante)

        beneficiario_id = header_form.cleaned_data["beneficiario_id"]
        if is_solicitante:
            beneficiario_id = request.user.pk

        try:
            requisicao = atualizar_rascunho_requisicao(
                requisicao_id=pk,
                ator=request.user,
                beneficiario_id=beneficiario_id,
                observacao=header_form.cleaned_data.get("observacao") or "",
                itens=itens,
            )
        except Exception as exc:
            header_form.add_error(None, str(exc))
            return self._render_422(request, pk, req, header_form, item_formset, is_solicitante)

        acao = request.POST.get("acao", "salvar")
        if acao == "enviar":
            try:
                enviar_para_autorizacao(requisicao=requisicao, ator=request.user)
            except Exception as exc:
                header_form.add_error(None, str(exc))
                return self._render_422(request, pk, req, header_form, item_formset, is_solicitante)

        if getattr(request, "htmx", False):
            from django_htmx.http import HttpResponseClientRedirect

            return HttpResponseClientRedirect(reverse("web:requisitions_mine"))

        from django.shortcuts import redirect

        return redirect("web:requisitions_mine")

    def _render_422(self, request, pk, req, header_form, item_formset, is_solicitante):
        ctx = {
            "header_form": header_form,
            "item_formset": item_formset,
            "is_solicitante": is_solicitante,
            "beneficiario_display": req.beneficiario.nome_completo if req else "",
            "material_nomes": {},
            "page_title": "Editar rascunho",
            "form_action": reverse("web:requisition_edit", args=[pk]),
            "acao_enviar_label": "Enviar para autorização",
            "requisicao": req,
        }
        ctx.update(_nav_context(request))
        if getattr(request, "htmx", False):
            return render(request, _FORM_PARTIAL_TEMPLATE, ctx, status=422)
        return render(request, _FORM_FULL_TEMPLATE, ctx, status=422)


def material_search_view(request):
    """GET HTMX — busca materiais para lookup no form de item."""
    from django.http import HttpResponseNotAllowed

    from apps.materials.selectors import buscar_materiais_para_requisicao
    from apps.web.htmx import htmx_session_expired

    if not request.user.is_authenticated:
        return htmx_session_expired(reverse("web:login"))

    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    q = request.GET.get("q", "").strip()
    item_idx = request.GET.get("idx", "0")

    materiais = buscar_materiais_para_requisicao(q)

    return render(
        request,
        _MATERIAL_RESULTS_TEMPLATE,
        {"materiais": materiais, "item_idx": item_idx, "q": q},
    )


def beneficiary_search_view(request):
    """GET HTMX — busca beneficiários no escopo do criador."""
    from django.http import HttpResponseNotAllowed

    from apps.users.selectors import buscar_beneficiarios_no_escopo
    from apps.web.htmx import htmx_session_expired

    if not request.user.is_authenticated:
        return htmx_session_expired(reverse("web:login"))

    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    q = request.GET.get("q", "").strip()
    beneficiarios = buscar_beneficiarios_no_escopo(q, request.user)

    return render(
        request,
        _BENEFICIARY_RESULTS_TEMPLATE,
        {"beneficiarios": beneficiarios, "q": q},
    )


def requisition_item_add_view(request):
    """GET HTMX — retorna nova linha de item para o formset."""
    from django.http import HttpResponseNotAllowed

    from apps.requisitions.forms import ItemRequisicaoForm
    from apps.web.htmx import htmx_session_expired

    if not request.user.is_authenticated:
        return htmx_session_expired(reverse("web:login"))

    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    try:
        total = int(request.GET.get("total", "1"))
    except ValueError, TypeError:
        total = 1

    idx = total
    new_total = total + 1

    form = ItemRequisicaoForm(prefix=f"form-{idx}")

    return render(
        request,
        _ITEM_ROW_TEMPLATE,
        {"form": form, "idx": idx, "new_total": new_total, "material_nomes": {}},
    )


def requisition_send_view(request, pk):
    """POST — envia rascunho para autorização."""
    from django.http import Http404, HttpResponseNotAllowed
    from django.shortcuts import redirect

    from apps.requisitions.models import Requisicao, StatusRequisicao
    from apps.requisitions.policies import (
        pode_manipular_pre_autorizacao,
        pode_visualizar_requisicao,
    )
    from apps.requisitions.services import enviar_para_autorizacao

    if not request.user.is_authenticated:
        from django.shortcuts import redirect as redir

        return redir("web:login")

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        req = Requisicao.objects.select_related(
            "criador", "beneficiario", "setor_beneficiario"
        ).get(pk=pk)
    except Requisicao.DoesNotExist:
        raise Http404

    if not pode_visualizar_requisicao(request.user, req):
        raise Http404

    if not pode_manipular_pre_autorizacao(request.user, req):
        raise Http404

    if req.status != StatusRequisicao.RASCUNHO:
        raise Http404

    try:
        enviar_para_autorizacao(requisicao=req, ator=request.user)
    except Exception:
        pass  # TODO: surface error via session message when flash messages added

    if getattr(request, "htmx", False):
        from django_htmx.http import HttpResponseClientRedirect

        return HttpResponseClientRedirect(reverse("web:requisitions_mine"))

    return redirect("web:requisitions_mine")
