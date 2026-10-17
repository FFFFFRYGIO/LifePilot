"""Google Tasks API client."""

from collections.abc import Iterator
from typing import Any

from ..models import Provider
from .base import ApiClient


class GoogleTasksClient(ApiClient):
    provider = Provider.GOOGLE
    base_url = "https://tasks.googleapis.com/tasks/v1"

    def _paginate(self, path: str, params: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
        params = dict(params or {})
        while True:
            page = self._send("GET", path, params=params).json()
            yield from page.get("items", [])
            token = page.get("nextPageToken")
            if not token:
                return
            params["pageToken"] = token

    def list_task_lists(self) -> list[dict[str, Any]]:
        return list(self._paginate("/users/@me/lists", {"maxResults": 100}))
