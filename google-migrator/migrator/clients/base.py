from types import TracebackType
from typing import Any, Self

import httpx

from ..http import RetryPolicy, new_client
from ..models import Provider
from ..oauth import get_access_token


class ApiError(Exception):
    def __init__(self, response: httpx.Response) -> None:
        request = response.request
        super().__init__(f"{request.method} {request.url} -> {response.status_code}: {response.text[:500]}")
        self.response = response
        self.status_code = response.status_code


class ApiClient:
    provider: Provider
    base_url: str

    def __init__(self, http: httpx.Client | None = None, retry: RetryPolicy | None = None) -> None:
        self.http = http or new_client()
        self.retry = retry or RetryPolicy()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self.http.close()

    def _url(self, path_or_url: str) -> str:
        return path_or_url if path_or_url.startswith("https://") else self.base_url + path_or_url

    def _send(self, method: str, path_or_url: str, **kwargs: Any) -> httpx.Response:
        url = self._url(path_or_url)
        extra_headers = kwargs.pop("headers", {})
        for force_refresh in (False, True):
            token = get_access_token(self.provider, force_refresh=force_refresh)
            headers = {**extra_headers, "Authorization": f"Bearer {token}"}
            response = self.retry.send(self.http, method, url, headers=headers, **kwargs)
            # One transparent retry with a freshly refreshed token if the access token was rejected.
            if response.status_code != 401:
                break
        if response.is_error:
            raise ApiError(response)
        return response
