from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx
import pytest

from migrator.http import RetriesExhausted, RetryPolicy, parse_retry_after

URL = "https://api.example.com/x"


def policy(slept: list[float], **kwargs) -> RetryPolicy:
    return RetryPolicy(sleep=slept.append, rng=lambda: 1.0, **kwargs)


def test_429_respects_retry_after_seconds(respx_mock):
    route = respx_mock.get(URL).mock(
        side_effect=[httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(200, json={"ok": 1})]
    )
    slept: list[float] = []
    with httpx.Client() as client:
        response = policy(slept).send(client, "GET", URL)
    assert response.status_code == 200
    assert route.call_count == 2
    assert slept == [7.0]


def test_retry_after_http_date():
    now = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
    header = format_datetime(now + timedelta(seconds=30), usegmt=True)
    assert parse_retry_after(header, now=now) == 30.0
    assert parse_retry_after("garbage") is None
    assert parse_retry_after(None) is None
    assert parse_retry_after("-5") == 0.0


def test_exponential_backoff_without_retry_after(respx_mock):
    respx_mock.get(URL).mock(
        side_effect=[httpx.Response(503), httpx.Response(503), httpx.Response(503), httpx.Response(200)]
    )
    slept: list[float] = []
    with httpx.Client() as client:
        policy(slept, base_delay=1.0).send(client, "GET", URL)
    assert slept == [1.0, 2.0, 4.0]


def test_backoff_is_capped(respx_mock):
    respx_mock.get(URL).mock(side_effect=[httpx.Response(500)] * 5 + [httpx.Response(200)])
    slept: list[float] = []
    with httpx.Client() as client:
        policy(slept, base_delay=10.0, max_delay=15.0).send(client, "GET", URL)
    assert max(slept) == 15.0


def test_gives_up_after_max_attempts(respx_mock):
    route = respx_mock.get(URL).mock(return_value=httpx.Response(429, headers={"Retry-After": "1"}))
    slept: list[float] = []
    with httpx.Client() as client, pytest.raises(RetriesExhausted) as exc:
        policy(slept, max_attempts=3).send(client, "GET", URL)
    assert route.call_count == 3
    assert len(slept) == 2
    assert exc.value.response.status_code == 429


def test_huge_retry_after_is_capped(respx_mock):
    respx_mock.get(URL).mock(
        side_effect=[httpx.Response(429, headers={"Retry-After": "99999"}), httpx.Response(200)]
    )
    slept: list[float] = []
    with httpx.Client() as client:
        policy(slept).send(client, "GET", URL)
    assert slept == [300.0]


def test_google_403_rate_limit_is_retried(respx_mock):
    body = {"error": {"code": 403, "errors": [{"reason": "userRateLimitExceeded"}]}}
    respx_mock.get(URL).mock(side_effect=[httpx.Response(403, json=body), httpx.Response(200)])
    slept: list[float] = []
    with httpx.Client() as client:
        assert policy(slept).send(client, "GET", URL).status_code == 200
    assert len(slept) == 1


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_non_retryable_errors_return_immediately(respx_mock, status):
    route = respx_mock.get(URL).mock(return_value=httpx.Response(status, json={"error": {"errors": []}}))
    slept: list[float] = []
    with httpx.Client() as client:
        assert policy(slept).send(client, "GET", URL).status_code == status
    assert route.call_count == 1
    assert slept == []
