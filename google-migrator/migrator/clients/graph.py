"""Microsoft Graph To Do client. Strictly read-only: anything but GET is refused before it hits the wire."""

from collections.abc import Iterator
from typing import Any

import httpx

from ..models import Provider
from .base import ApiClient


class ReadOnlyViolation(RuntimeError):
    pass


class GraphClient(ApiClient):
    provider = Provider.MICROSOFT
    base_url = "https://graph.microsoft.com/v1.0"

    def _send(self, method: str, path_or_url: str, **kwargs: Any) -> httpx.Response:
        if method.upper() != "GET":
            raise ReadOnlyViolation(
                f"Microsoft To Do jest tylko do odczytu; odrzucono {method} {path_or_url}"
            )
        if not self._url(path_or_url).startswith(self.base_url + "/"):
            raise ReadOnlyViolation(f"Nieoczekiwany host dla Graph: {path_or_url}")
        return super()._send(method, path_or_url, **kwargs)

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        result: dict[str, Any] = self._send("GET", path, params=params).json()
        return result

    def paginate(self, path: str, params: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
        """Yield items across pages, following @odata.nextLink (which already carries the query)."""
        page = self.get(path, params)
        while True:
            yield from page.get("value", [])
            next_link = page.get("@odata.nextLink")
            if not next_link:
                return
            page = self.get(next_link)

    def list_task_lists(self) -> list[dict[str, Any]]:
        return list(self.paginate("/me/todo/lists"))
