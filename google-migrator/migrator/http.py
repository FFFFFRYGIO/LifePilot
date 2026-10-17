"""HTTP with throttling-aware retries shared by the Graph and Google clients.

Retries: 429, 5xx, and Google's 403 rate-limit reasons. `Retry-After` (seconds or HTTP-date)
wins over the computed backoff; otherwise exponential backoff with full jitter.
"""

import logging
import random
import ssl
import time
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from functools import cache
from typing import Any

import certifi
import httpx

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
GOOGLE_RATE_LIMIT_REASONS = {"rateLimitExceeded", "userRateLimitExceeded", "quotaExceeded"}
MAX_RETRY_AFTER = 300.0
DEFAULT_TIMEOUT = httpx.Timeout(30.0)


@cache
def _ssl_context() -> ssl.SSLContext:
    # Building a context loads the CA bundle, which is slow; do it once per process.
    return ssl.create_default_context(cafile=certifi.where())


def new_client() -> httpx.Client:
    return httpx.Client(timeout=DEFAULT_TIMEOUT, verify=_ssl_context())


class RetriesExhausted(Exception):
    def __init__(self, response: httpx.Response) -> None:
        super().__init__(f"{response.request.method} {response.request.url} -> {response.status_code}")
        self.response = response


def parse_retry_after(value: str | None, now: datetime | None = None) -> float | None:
    if not value:
        return None
    value = value.strip()
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max(0.0, (when - (now or datetime.now(UTC))).total_seconds())


def _is_google_rate_limit(response: httpx.Response) -> bool:
    if response.status_code != 403:
        return False
    try:
        errors = response.json().get("error", {}).get("errors", [])
    except ValueError:
        return False
    return any(e.get("reason") in GOOGLE_RATE_LIMIT_REASONS for e in errors)


def is_retryable(response: httpx.Response) -> bool:
    return response.status_code in RETRYABLE_STATUS or _is_google_rate_limit(response)


class RetryPolicy:
    def __init__(
        self,
        max_attempts: int = 6,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        sleep: Callable[[float], None] | None = None,
        rng: Callable[[], float] = random.random,
    ) -> None:
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._sleep = sleep
        self.rng = rng

    def delay_for(self, attempt: int, response: httpx.Response) -> float:
        retry_after = parse_retry_after(response.headers.get("Retry-After"))
        if retry_after is not None:
            return min(retry_after, MAX_RETRY_AFTER)
        cap = min(self.max_delay, self.base_delay * 2 ** (attempt - 1))
        return float(cap * self.rng())

    def send(self, client: httpx.Client, method: str, url: str, **kwargs: Any) -> httpx.Response:
        for attempt in range(1, self.max_attempts + 1):
            response = client.request(method, url, **kwargs)
            if not is_retryable(response):
                return response
            if attempt == self.max_attempts:
                raise RetriesExhausted(response)
            delay = self.delay_for(attempt, response)
            logger.warning(
                "%s %s -> %s, retry %d/%d in %.1fs",
                method,
                url,
                response.status_code,
                attempt,
                self.max_attempts - 1,
                delay,
            )
            # Resolved at call time so tests can patch time.sleep globally.
            (self._sleep or time.sleep)(delay)
        raise AssertionError("unreachable")
