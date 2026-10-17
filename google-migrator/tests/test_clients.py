import httpx
import pytest

from migrator.clients.base import ApiError
from migrator.clients.graph import GraphClient, ReadOnlyViolation
from migrator.clients.gtasks import GoogleTasksClient

GRAPH = "https://graph.microsoft.com/v1.0"
TASKS = "https://tasks.googleapis.com/tasks/v1"


@pytest.mark.parametrize("method", ["POST", "PATCH", "PUT", "DELETE", "post"])
def test_graph_client_refuses_any_write(method, respx_mock, ms_connection):
    with GraphClient() as client, pytest.raises(ReadOnlyViolation):
        client._send(method, "/me/todo/lists")
    assert not respx_mock.calls


def test_graph_client_refuses_foreign_host(respx_mock, ms_connection):
    with GraphClient() as client, pytest.raises(ReadOnlyViolation):
        client.get("https://evil.example.com/v1.0/me")


def test_graph_lists_follow_next_link(respx_mock, ms_connection):
    next_link = f"{GRAPH}/me/todo/lists?$skiptoken=abc"
    respx_mock.get(f"{GRAPH}/me/todo/lists", params={"$skiptoken": "abc"}).mock(
        return_value=httpx.Response(200, json={"value": [{"id": "2", "displayName": "B"}]})
    )
    respx_mock.get(f"{GRAPH}/me/todo/lists").mock(
        return_value=httpx.Response(
            200, json={"value": [{"id": "1", "displayName": "A"}], "@odata.nextLink": next_link}
        )
    )
    with GraphClient() as client:
        lists = client.list_task_lists()
    assert [x["displayName"] for x in lists] == ["A", "B"]
    assert respx_mock.calls.last.request.headers["Authorization"] == "Bearer microsoft-access"


def test_graph_429_is_retried_with_retry_after(respx_mock, ms_connection, no_sleep):
    respx_mock.get(f"{GRAPH}/me/todo/lists").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "3"}),
            httpx.Response(200, json={"value": []}),
        ]
    )
    with GraphClient() as client:
        assert client.list_task_lists() == []
    assert no_sleep == [3.0]


def test_google_lists_follow_page_token(respx_mock, google_connection):
    respx_mock.get(f"{TASKS}/users/@me/lists", params={"pageToken": "p2"}).mock(
        return_value=httpx.Response(200, json={"items": [{"id": "g2", "title": "Two"}]})
    )
    respx_mock.get(f"{TASKS}/users/@me/lists").mock(
        return_value=httpx.Response(
            200, json={"items": [{"id": "g1", "title": "One"}], "nextPageToken": "p2"}
        )
    )
    with GoogleTasksClient() as client:
        assert [x["title"] for x in client.list_task_lists()] == ["One", "Two"]


def test_401_triggers_one_forced_refresh(respx_mock, google_connection):
    respx_mock.post("https://oauth2.googleapis.com/token").mock(
        return_value=httpx.Response(200, json={"access_token": "fresh", "expires_in": 3600})
    )
    respx_mock.get(f"{TASKS}/users/@me/lists").mock(
        side_effect=[httpx.Response(401), httpx.Response(200, json={"items": []})]
    )
    with GoogleTasksClient() as client:
        assert client.list_task_lists() == []
    assert respx_mock.calls.last.request.headers["Authorization"] == "Bearer fresh"


def test_api_error_is_raised_for_non_retryable_failure(respx_mock, google_connection):
    respx_mock.get(f"{TASKS}/users/@me/lists").mock(return_value=httpx.Response(404, text="nope"))
    with GoogleTasksClient() as client, pytest.raises(ApiError) as exc:
        client.list_task_lists()
    assert exc.value.status_code == 404
