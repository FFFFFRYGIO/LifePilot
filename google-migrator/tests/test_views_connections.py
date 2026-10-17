from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from django.urls import reverse

from migrator.models import Connection, Provider

pytestmark = pytest.mark.django_db

MS_TOKEN_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"


def test_login_is_required(client):
    response = client.get(reverse("migrator:connections"))
    assert response.status_code == 302
    assert response["Location"].startswith(reverse("login"))


def test_connections_page_shows_both_providers(user_client, google_connection):
    response = user_client.get(reverse("migrator:connections"))
    content = response.content.decode()
    assert response.status_code == 200
    assert "Microsoft To Do" in content
    assert "Google Tasks" in content
    assert "me@google.example" in content
    assert "google-access" not in content  # tokens never rendered


def test_reauth_required_is_clearly_shown(user_client, google_connection):
    google_connection.status = Connection.Status.REAUTH_REQUIRED
    google_connection.last_error = "Refresh token wygasł"
    google_connection.save()
    content = user_client.get(reverse("migrator:connections")).content.decode()
    assert "wymaga ponownego połączenia" in content
    assert "Refresh token wygasł" in content


def _start(user_client, provider: str) -> str:
    response = user_client.post(reverse("migrator:oauth_start", args=[provider]))
    assert response.status_code == 302
    return str(parse_qs(urlparse(response["Location"]).query)["state"][0])


def test_full_microsoft_oauth_flow(user_client, respx_mock):
    state = _start(user_client, "microsoft")
    respx_mock.post(MS_TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "a", "refresh_token": "r", "expires_in": 3600})
    )
    respx_mock.get("https://graph.microsoft.com/v1.0/me").mock(
        return_value=httpx.Response(200, json={"userPrincipalName": "me@outlook.com"})
    )

    response = user_client.get(
        reverse("migrator:oauth_callback", args=["microsoft"]), {"code": "c", "state": state}
    )

    assert response.status_code == 302
    conn = Connection.objects.get(provider=Provider.MICROSOFT)
    assert conn.account_email == "me@outlook.com"
    assert conn.refresh_token == "r"


def test_callback_rejects_wrong_state(user_client, respx_mock):
    _start(user_client, "google")
    response = user_client.get(
        reverse("migrator:oauth_callback", args=["google"]), {"code": "c", "state": "forged"}, follow=True
    )
    assert "nieprawidłowy parametr state" in response.content.decode()
    assert not respx_mock.calls
    assert not Connection.objects.exists()


def test_callback_state_is_single_use(user_client, respx_mock):
    state = _start(user_client, "google")
    url = reverse("migrator:oauth_callback", args=["google"])
    user_client.get(url, {"error": "access_denied", "state": state})
    response = user_client.get(url, {"code": "c", "state": state}, follow=True)
    assert "nieprawidłowy parametr state" in response.content.decode()


def test_callback_surfaces_provider_error(user_client):
    state = _start(user_client, "google")
    response = user_client.get(
        reverse("migrator:oauth_callback", args=["google"]),
        {"error": "access_denied", "state": state},
        follow=True,
    )
    assert "access_denied" in response.content.decode()


def test_unknown_provider_is_404(user_client):
    assert user_client.post(reverse("migrator:oauth_start", args=["dropbox"])).status_code == 404


def test_disconnect_only_removes_local_tokens(user_client, google_connection, respx_mock):
    user_client.post(reverse("migrator:disconnect", args=["google"]))
    assert not Connection.objects.filter(provider=Provider.GOOGLE).exists()
    assert not respx_mock.calls


def test_lists_fragment_shows_lists_from_both_sides(
    user_client, ms_connection, google_connection, respx_mock
):
    respx_mock.get("https://graph.microsoft.com/v1.0/me/todo/lists").mock(
        return_value=httpx.Response(
            200, json={"value": [{"id": "1", "displayName": "Zakupy", "wellknownListName": "none"}]}
        )
    )
    respx_mock.get("https://tasks.googleapis.com/tasks/v1/users/@me/lists").mock(
        return_value=httpx.Response(
            200, json={"items": [{"id": "g", "title": "My Tasks", "updated": "2026"}]}
        )
    )
    content = user_client.get(reverse("migrator:lists_fragment")).content.decode()
    assert "Zakupy" in content
    assert "My Tasks" in content


def test_lists_fragment_reports_missing_connection(user_client, respx_mock):
    content = user_client.get(reverse("migrator:lists_fragment")).content.decode()
    assert content.count("Brak połączenia.") == 2
