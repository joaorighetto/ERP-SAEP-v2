from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from apps.users.forms import LoginForm

_LOGIN_TEMPLATE = "web/pages/auth/login.html"
_LOGGED_OUT_TEMPLATE = "web/pages/auth/logged_out.html"


def _safe_next(request) -> str:
    """Return `next` param if internal; fallback to web:home."""
    from django.urls import reverse

    next_url = request.POST.get("next") or request.GET.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return reverse("web:home")


class LoginView:
    """Login HTML server-rendered. Funciona sem JavaScript."""

    def dispatch(self, request, *args, **kwargs):
        if request.method == "GET":
            return self.get(request)
        if request.method == "POST":
            return self.post(request)
        return HttpResponseNotAllowed(["GET", "POST"])

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("web:home")
        form = LoginForm()
        return render(request, _LOGIN_TEMPLATE, {"form": form, "next": request.GET.get("next", "")})

    def post(self, request):
        form = LoginForm(data=request.POST)
        if not form.is_valid():
            return render(
                request,
                _LOGIN_TEMPLATE,
                {"form": form, "next": request.POST.get("next", "")},
                status=422,
            )

        user = authenticate(
            request,
            username=form.cleaned_data["matricula_funcional"],
            password=form.cleaned_data["password"],
        )
        if user is None:
            return render(
                request,
                _LOGIN_TEMPLATE,
                {
                    "form": form,
                    "next": request.POST.get("next", ""),
                    "auth_error": "Matrícula funcional ou senha inválidas.",
                },
                status=200,
            )

        login(request, user)
        return redirect(_safe_next(request))

    @classmethod
    def as_view(cls):
        def view(request, *args, **kwargs):
            return cls().dispatch(request, *args, **kwargs)

        return view


class LogoutView:
    """Logout via POST + CSRF. GET redireciona sem matar sessão."""

    def dispatch(self, request, *args, **kwargs):
        if request.method == "POST":
            return self.post(request)
        # GET: não encerra sessão — redireciona para login
        return redirect("web:login")

    def post(self, request):
        logout(request)
        return redirect("web:logged_out")

    @classmethod
    def as_view(cls):
        def view(request, *args, **kwargs):
            return cls().dispatch(request, *args, **kwargs)

        return view


class LoggedOutView:
    """Página pública após encerramento de sessão."""

    def dispatch(self, request, *args, **kwargs):
        if request.method == "GET":
            return render(request, _LOGGED_OUT_TEMPLATE)
        return HttpResponseNotAllowed(["GET"])

    @classmethod
    def as_view(cls):
        def view(request, *args, **kwargs):
            return cls().dispatch(request, *args, **kwargs)

        return view
