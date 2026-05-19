from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.web.navigation import get_navigation_context


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "web/pages/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(get_navigation_context(self.request))
        return ctx
