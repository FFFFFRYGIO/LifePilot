"""Google Calendar client: calendars, sharing (ACL) and events."""

from collections.abc import Iterator
from typing import Any

from ..models import Provider
from .base import ApiClient


class GoogleCalendarClient(ApiClient):
    provider = Provider.GOOGLE
    base_url = "https://www.googleapis.com/calendar/v3"

    def _paginate(self, path: str, params: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
        params = dict(params or {})
        while True:
            page = self._send("GET", path, params=params).json()
            yield from page.get("items", [])
            token = page.get("nextPageToken")
            if not token:
                return
            params["pageToken"] = token

    # --- calendars --------------------------------------------------------

    def list_calendars(self) -> list[dict[str, Any]]:
        return list(self._paginate("/users/me/calendarList", {"maxResults": 250}))

    def find_calendar_by_summary(self, summary: str) -> dict[str, Any] | None:
        """Match on the calendar's own summary; summaryOverride is a per-user rename and is ignored."""
        for calendar in self.list_calendars():
            if calendar.get("summary") == summary:
                return calendar
        return None

    def create_calendar(self, summary: str, *, time_zone: str, description: str = "") -> dict[str, Any]:
        body = {"summary": summary, "timeZone": time_zone}
        if description:
            body["description"] = description
        result: dict[str, Any] = self._send("POST", "/calendars", json=body).json()
        return result

    # --- sharing ----------------------------------------------------------

    def list_acl(self, calendar_id: str) -> list[dict[str, Any]]:
        return list(self._paginate(f"/calendars/{calendar_id}/acl"))

    def share_with(self, calendar_id: str, email: str, *, role: str = "writer") -> dict[str, Any]:
        """Grant `email` access. Idempotent: an existing rule with the same role is returned as-is."""
        for rule in self.list_acl(calendar_id):
            scope = rule.get("scope", {})
            if scope.get("type") == "user" and scope.get("value", "").lower() == email.lower():
                if rule.get("role") == role:
                    return rule
                break
        body = {"role": role, "scope": {"type": "user", "value": email}}
        result: dict[str, Any] = self._send(
            "POST", f"/calendars/{calendar_id}/acl", json=body, params={"sendNotifications": "true"}
        ).json()
        return result

    # --- events -----------------------------------------------------------

    def search_events(self, calendar_id: str, query: str) -> list[dict[str, Any]]:
        return list(
            self._paginate(
                f"/calendars/{calendar_id}/events",
                {"q": query, "maxResults": 250, "showDeleted": "false"},
            )
        )

    def create_event(self, calendar_id: str, body: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = self._send("POST", f"/calendars/{calendar_id}/events", json=body).json()
        return result
