"""OAuth2 authorization code + PKCE for Microsoft (personal accounts) and Google, plus token refresh."""

import base64
import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any
from urllib.parse import urlencode

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .http import RetryPolicy, new_client
from .models import Connection, Provider

logger = logging.getLogger(__name__)

REFRESH_MARGIN = timedelta(minutes=5)

# Read-only on the Microsoft side by design: the migrator never modifies Microsoft To Do.
MS_SCOPES = ("offline_access", "User.Read", "Tasks.Read")
GOOGLE_SCOPES = ("openid", "email", "https://www.googleapis.com/auth/tasks")


class OAuthError(Exception):
    pass


class NotConnected(OAuthError):
    pass


class ReauthRequired(OAuthError):
    """Refresh token expired or revoked; the user must reconnect in the UI."""


@dataclass(frozen=True)
class ProviderConfig:
    provider: Provider
    authorize_url: str
    token_url: str
    userinfo_url: str
    scopes: tuple[str, ...]
    client_id: str
    client_secret: str
    extra_authorize_params: dict[str, str] = field(default_factory=dict)

    @property
    def redirect_uri(self) -> str:
        return str(settings.BASE_URL) + reverse("migrator:oauth_callback", args=[self.provider.value])

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)


def get_config(provider: Provider | str) -> ProviderConfig:
    provider = Provider(provider)
    if provider is Provider.MICROSOFT:
        authority = settings.MS_AUTHORITY.rstrip("/")
        return ProviderConfig(
            provider=provider,
            authorize_url=f"{authority}/oauth2/v2.0/authorize",
            token_url=f"{authority}/oauth2/v2.0/token",
            userinfo_url="https://graph.microsoft.com/v1.0/me",
            scopes=MS_SCOPES,
            client_id=settings.MS_CLIENT_ID,
            client_secret=settings.MS_CLIENT_SECRET,
            extra_authorize_params={"response_mode": "query", "prompt": "select_account"},
        )
    return ProviderConfig(
        provider=provider,
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",  # noqa: S106 (URL, not a secret)
        userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
        scopes=GOOGLE_SCOPES,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        # offline + consent guarantees a refresh token on every (re)connect.
        extra_authorize_params={"access_type": "offline", "prompt": "consent"},
    )


# --- PKCE -----------------------------------------------------------------


def new_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)[:128]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


@dataclass(frozen=True)
class AuthorizationRequest:
    url: str
    state: str
    code_verifier: str


def build_authorization(provider: Provider | str) -> AuthorizationRequest:
    config = get_config(provider)
    if not config.is_configured:
        raise OAuthError(f"Brak client ID/secret dla {config.provider.label} w konfiguracji (.env)")
    verifier, challenge = new_pkce_pair()
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": config.client_id,
        "response_type": "code",
        "redirect_uri": config.redirect_uri,
        "scope": " ".join(config.scopes),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        **config.extra_authorize_params,
    }
    return AuthorizationRequest(f"{config.authorize_url}?{urlencode(params)}", state, verifier)


# --- token endpoint -------------------------------------------------------


@dataclass(frozen=True)
class TokenSet:
    access_token: str
    refresh_token: str | None
    expires_in: int
    scope: str

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> "TokenSet":
        return cls(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_in=int(data.get("expires_in", 3600)),
            scope=data.get("scope", ""),
        )


def _token_request(config: ProviderConfig, data: dict[str, str]) -> TokenSet:
    payload = {"client_id": config.client_id, "client_secret": config.client_secret, **data}
    with new_client() as client:
        response = RetryPolicy(max_attempts=3).send(client, "POST", config.token_url, data=payload)
    if response.status_code == 200:
        return TokenSet.from_response(response.json())
    try:
        body = response.json()
    except ValueError:
        body = {}
    error = body.get("error", "")
    description = body.get("error_description", response.text[:300])
    if error == "invalid_grant":
        raise ReauthRequired(description or "invalid_grant")
    raise OAuthError(f"{config.provider.label}: {response.status_code} {error} {description}".strip())


def exchange_code(provider: Provider | str, code: str, code_verifier: str) -> TokenSet:
    config = get_config(provider)
    return _token_request(
        config,
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.redirect_uri,
            "code_verifier": code_verifier,
        },
    )


def fetch_account_email(provider: Provider | str, access_token: str) -> str:
    config = get_config(provider)
    with new_client() as client:
        response = RetryPolicy(max_attempts=3).send(
            client, "GET", config.userinfo_url, headers={"Authorization": f"Bearer {access_token}"}
        )
    if response.status_code != 200:
        logger.warning("userinfo for %s failed: %s", provider, response.status_code)
        return ""
    data = response.json()
    return str(data.get("email") or data.get("mail") or data.get("userPrincipalName") or "")


def save_connection(provider: Provider | str, tokens: TokenSet, account_email: str) -> Connection:
    provider = Provider(provider)
    if not tokens.refresh_token:
        raise OAuthError(f"{provider.label} nie zwrócił refresh tokena; połącz ponownie")
    connection, _ = Connection.objects.update_or_create(
        provider=provider,
        defaults={
            "account_email": account_email,
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "expires_at": timezone.now() + timedelta(seconds=tokens.expires_in),
            "scopes": tokens.scope,
            "status": Connection.Status.OK,
            "last_error": "",
        },
    )
    return connection


# --- access for API clients -----------------------------------------------


def get_access_token(provider: Provider | str, *, force_refresh: bool = False) -> str:
    """Return a valid access token, refreshing it (under a row lock) when close to expiry."""
    provider = Provider(provider)
    with transaction.atomic():
        connection = Connection.objects.select_for_update().filter(provider=provider).first()
        if connection is None:
            raise NotConnected(f"{provider.label}: brak połączenia")
        if connection.status == Connection.Status.REAUTH_REQUIRED:
            raise ReauthRequired(connection.last_error or f"{provider.label}: połącz ponownie")
        if not force_refresh and not connection.expires_within(REFRESH_MARGIN):
            return str(connection.access_token)
        try:
            tokens = _token_request(
                get_config(provider),
                {"grant_type": "refresh_token", "refresh_token": connection.refresh_token},
            )
        except ReauthRequired as exc:
            connection.status = Connection.Status.REAUTH_REQUIRED
            connection.last_error = f"Refresh token wygasł lub został odwołany: {exc}"
            connection.save(update_fields=["status", "last_error", "updated_at"])
            logger.error("%s refresh token rejected: %s", provider, exc)
            # Raised after the atomic block so the status change is committed, not rolled back.
            reauth = ReauthRequired(connection.last_error)
        else:
            connection.access_token = tokens.access_token
            if tokens.refresh_token:  # Microsoft rotates refresh tokens; Google usually does not.
                connection.refresh_token = tokens.refresh_token
            connection.expires_at = timezone.now() + timedelta(seconds=tokens.expires_in)
            connection.last_error = ""
            connection.save()
            return str(connection.access_token)
    raise reauth
