import base64
import hashlib
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from migrator import oauth
from migrator.models import Connection, Provider
from tests.conftest import make_connection

MS_TOKEN_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


def test_pkce_challenge_is_s256_of_verifier():
    verifier, challenge = oauth.new_pkce_pair()
    assert 43 <= len(verifier) <= 128
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert challenge == expected


def test_microsoft_authorization_url_is_personal_and_read_only():
    auth = oauth.build_authorization(Provider.MICROSOFT)
    url = urlparse(auth.url)
    q = {k: v[0] for k, v in parse_qs(url.query).items()}

    assert url.netloc == "login.microsoftonline.com"
    assert url.path == "/consumers/oauth2/v2.0/authorize"
    assert q["code_challenge_method"] == "S256"
    assert q["state"] == auth.state
    assert q["redirect_uri"] == "http://testserver/oauth/microsoft/callback"
    scopes = set(q["scope"].split())
    assert scopes == {"offline_access", "User.Read", "Tasks.Read"}
    assert not any("Write" in s for s in scopes)


def test_google_authorization_url_requests_offline_access():
    q = parse_qs(urlparse(oauth.build_authorization(Provider.GOOGLE).url).query)
    assert q["access_type"] == ["offline"]
    assert q["prompt"] == ["consent"]
    assert "https://www.googleapis.com/auth/tasks" in q["scope"][0].split()


def test_unconfigured_provider_raises(settings):
    settings.GOOGLE_CLIENT_ID = ""
    with pytest.raises(oauth.OAuthError):
        oauth.build_authorization(Provider.GOOGLE)


def test_exchange_code_sends_verifier(respx_mock):
    route = respx_mock.post(MS_TOKEN_URL).mock(
        return_value=httpx.Response(
            200, json={"access_token": "a", "refresh_token": "r", "expires_in": 3600, "scope": "Tasks.Read"}
        )
    )
    tokens = oauth.exchange_code(Provider.MICROSOFT, "the-code", "the-verifier")
    body = parse_qs(route.calls.last.request.content.decode())
    assert body["code_verifier"] == ["the-verifier"]
    assert body["grant_type"] == ["authorization_code"]
    assert tokens.refresh_token == "r"


@pytest.mark.django_db
def test_valid_token_is_returned_without_refresh(respx_mock):
    make_connection(Provider.GOOGLE, expires_in=timedelta(hours=1))
    assert oauth.get_access_token(Provider.GOOGLE) == "google-access"
    assert not respx_mock.calls


@pytest.mark.django_db
def test_token_near_expiry_is_refreshed_and_rotated(respx_mock):
    make_connection(Provider.MICROSOFT, expires_in=timedelta(minutes=2))
    route = respx_mock.post(MS_TOKEN_URL).mock(
        return_value=httpx.Response(
            200, json={"access_token": "new-access", "refresh_token": "new-refresh", "expires_in": 3600}
        )
    )
    assert oauth.get_access_token(Provider.MICROSOFT) == "new-access"
    assert parse_qs(route.calls.last.request.content.decode())["refresh_token"] == ["microsoft-refresh"]
    conn = Connection.objects.get(provider=Provider.MICROSOFT)
    assert conn.refresh_token == "new-refresh"
    assert not conn.expires_within(timedelta(minutes=50))


@pytest.mark.django_db
def test_google_refresh_keeps_existing_refresh_token(respx_mock):
    make_connection(Provider.GOOGLE, expires_in=timedelta(seconds=-10))
    respx_mock.post(GOOGLE_TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "g2", "expires_in": 3599})
    )
    assert oauth.get_access_token(Provider.GOOGLE) == "g2"
    assert Connection.objects.get(provider=Provider.GOOGLE).refresh_token == "google-refresh"


@pytest.mark.django_db
def test_revoked_refresh_token_marks_reauth_required(respx_mock):
    make_connection(Provider.GOOGLE, expires_in=timedelta(seconds=-10))
    respx_mock.post(GOOGLE_TOKEN_URL).mock(
        return_value=httpx.Response(
            400, json={"error": "invalid_grant", "error_description": "Token has been expired or revoked."}
        )
    )
    with pytest.raises(oauth.ReauthRequired):
        oauth.get_access_token(Provider.GOOGLE)

    conn = Connection.objects.get(provider=Provider.GOOGLE)
    assert conn.status == Connection.Status.REAUTH_REQUIRED
    assert "expired or revoked" in conn.last_error

    # Subsequent calls fail fast without hitting the token endpoint again.
    calls_before = len(respx_mock.calls)
    with pytest.raises(oauth.ReauthRequired):
        oauth.get_access_token(Provider.GOOGLE)
    assert len(respx_mock.calls) == calls_before


@pytest.mark.django_db
def test_transient_refresh_error_does_not_mark_reauth(respx_mock, no_sleep):
    make_connection(Provider.GOOGLE, expires_in=timedelta(seconds=-10))
    respx_mock.post(GOOGLE_TOKEN_URL).mock(
        return_value=httpx.Response(400, json={"error": "invalid_request"})
    )
    with pytest.raises(oauth.OAuthError) as exc:
        oauth.get_access_token(Provider.GOOGLE)
    assert not isinstance(exc.value, oauth.ReauthRequired)
    assert Connection.objects.get(provider=Provider.GOOGLE).status == Connection.Status.OK


@pytest.mark.django_db
def test_not_connected():
    with pytest.raises(oauth.NotConnected):
        oauth.get_access_token(Provider.MICROSOFT)


@pytest.mark.django_db
def test_save_connection_requires_refresh_token():
    tokens = oauth.TokenSet(access_token="a", refresh_token=None, expires_in=3600, scope="")
    with pytest.raises(oauth.OAuthError):
        oauth.save_connection(Provider.GOOGLE, tokens, "x@example.com")
