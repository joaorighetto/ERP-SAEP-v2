"""HTMX response helpers for apps/web views.

Views must not write HTMX headers manually — use these helpers instead.
"""

from django.http import HttpResponse
from django.shortcuts import render
from django_htmx.http import (
    HttpResponseClientRedirect,
    HttpResponseClientRefresh,
    trigger_client_event,
)


def render_htmx(request, template, context, *, status=200):
    """Render an HTMX partial. Falls back to full page render for non-HTMX requests."""
    return render(request, template, context, status=status)


def htmx_redirect(url, *, status=200):
    """Send HX-Redirect header to navigate client-side."""
    return HttpResponseClientRedirect(url)


def htmx_refresh(*, status=200):
    """Send HX-Refresh header to reload the page."""
    return HttpResponseClientRefresh()


def htmx_trigger(response, event, payload=None, after="receive"):
    """Attach HX-Trigger header to an existing response.

    after: "receive" | "swap" | "settle"
    """
    return trigger_client_event(response, event, payload or {}, after=after)


def htmx_retarget(response, target):
    """Override the HTMX swap target via HX-Retarget header."""
    response["HX-Retarget"] = target
    return response


def htmx_validation_error(request, template, context):
    """Return 422 with form partial containing field errors."""
    return render(request, template, context, status=422)


def htmx_forbidden(request, template=None, context=None):
    """Return 403 with a safe feedback fragment — no internal data exposed."""
    if template:
        return render(request, template, context or {}, status=403)
    body = '<div id="global-errors" aria-live="assertive" aria-atomic="true" class="sr-only">Acesso negado.</div>'
    return HttpResponse(body, status=403, content_type="text/html")


def htmx_conflict(request, template=None, context=None):
    """Return 409 with conflict feedback and recommended next action."""
    if template:
        return render(request, template, context or {}, status=409)
    body = '<div id="global-errors" aria-live="assertive" aria-atomic="true" class="sr-only">Conflito detectado. Recarregue a página.</div>'
    return HttpResponse(body, status=409, content_type="text/html")


def htmx_session_expired(login_url):
    """Redirect to login when session expires — never inject login into partial."""
    return HttpResponseClientRedirect(login_url)
