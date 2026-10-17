import logging
from typing import Any

from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from . import oauth
from .clients.base import ApiError
from .clients.graph import GraphClient
from .clients.gtasks import GoogleTasksClient
from .http import RetriesExhausted
from .models import Connection, Provider

logger = logging.getLogger(__name__)

SESSION_KEY = "oauth_pending"


def _provider(value: str) -> Provider:
    try:
        return Provider(value)
    except ValueError as exc:
        raise Http404("Nieznany dostawca") from exc


@require_GET
def connections(request: HttpRequest) -> HttpResponse:
    existing = {c.provider: c for c in Connection.objects.all()}
    cards = []
    for provider in Provider:
        config = oauth.get_config(provider)
        cards.append(
            {
                "provider": provider,
                "connection": existing.get(provider.value),
                "configured": config.is_configured,
                "redirect_uri": config.redirect_uri,
                "scopes": config.scopes,
            }
        )
    return render(request, "migrator/connections.html", {"cards": cards})


@require_POST
def oauth_start(request: HttpRequest, provider: str) -> HttpResponse:
    p = _provider(provider)
    try:
        auth = oauth.build_authorization(p)
    except oauth.OAuthError as exc:
        messages.error(request, str(exc))
        return redirect("migrator:connections")
    pending = request.session.get(SESSION_KEY, {})
    pending[p.value] = {"state": auth.state, "verifier": auth.code_verifier}
    request.session[SESSION_KEY] = pending
    return HttpResponseRedirect(auth.url)


@require_GET
def oauth_callback(request: HttpRequest, provider: str) -> HttpResponse:
    p = _provider(provider)
    pending = request.session.get(SESSION_KEY, {}).pop(p.value, None)
    request.session.modified = True

    if error := request.GET.get("error"):
        messages.error(request, f"{p.label}: {error} {request.GET.get('error_description', '')}".strip())
        return redirect("migrator:connections")
    if not pending or request.GET.get("state") != pending["state"]:
        messages.error(request, f"{p.label}: nieprawidłowy parametr state. Spróbuj połączyć jeszcze raz.")
        return redirect("migrator:connections")
    code = request.GET.get("code")
    if not code:
        messages.error(request, f"{p.label}: brak kodu autoryzacji w odpowiedzi.")
        return redirect("migrator:connections")

    try:
        tokens = oauth.exchange_code(p, code, pending["verifier"])
        email = oauth.fetch_account_email(p, tokens.access_token)
        oauth.save_connection(p, tokens, email)
    except (oauth.OAuthError, RetriesExhausted) as exc:
        logger.exception("OAuth callback failed for %s", p)
        messages.error(request, f"{p.label}: nie udało się połączyć: {exc}")
    else:
        messages.success(request, f"Połączono z {p.label} ({email or 'konto bez adresu e-mail'}).")
    return redirect("migrator:connections")


@require_POST
def disconnect(request: HttpRequest, provider: str) -> HttpResponse:
    p = _provider(provider)
    Connection.objects.filter(provider=p).delete()
    messages.info(request, f"Usunięto lokalne tokeny {p.label}. Nic nie zostało zmienione po stronie usługi.")
    return redirect("migrator:connections")


def _fetch_lists(provider: Provider) -> dict[str, Any]:
    client_cls = GraphClient if provider is Provider.MICROSOFT else GoogleTasksClient
    try:
        with client_cls() as client:
            return {"items": client.list_task_lists(), "error": None}
    except oauth.NotConnected:
        return {"items": [], "error": "Brak połączenia."}
    except oauth.ReauthRequired as exc:
        return {"items": [], "error": f"Wymaga ponownego połączenia: {exc}"}
    except (ApiError, RetriesExhausted, oauth.OAuthError) as exc:
        logger.exception("Listing task lists failed for %s", provider)
        return {"items": [], "error": str(exc)}


@require_GET
def lists_fragment(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "migrator/_lists.html",
        {"ms": _fetch_lists(Provider.MICROSOFT), "google": _fetch_lists(Provider.GOOGLE)},
    )
