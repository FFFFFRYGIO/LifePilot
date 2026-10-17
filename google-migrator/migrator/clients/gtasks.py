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

    def create_task_list(self, title: str) -> dict[str, Any]:
        result: dict[str, Any] = self._send("POST", "/users/@me/lists", json={"title": title}).json()
        return result

    def find_task_list_by_title(self, title: str) -> dict[str, Any] | None:
        for task_list in self.list_task_lists():
            if task_list.get("title") == title:
                return task_list
        return None

    def list_tasks(self, task_list_id: str, *, show_completed: bool = False) -> list[dict[str, Any]]:
        return list(
            self._paginate(
                f"/lists/{task_list_id}/tasks",
                {"maxResults": 100, "showCompleted": str(show_completed).lower()},
            )
        )

    def create_task(self, task_list_id: str, body: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = self._send("POST", f"/lists/{task_list_id}/tasks", json=body).json()
        return result
