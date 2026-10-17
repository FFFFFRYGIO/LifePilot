"""Birthdays and other yearly occasions: Microsoft To Do -> Google Calendar + Google Tasks.

One source task becomes two things in Google:

* a **yearly all-day event** in a dedicated calendar (the thing itself), and
* a **Google task** on the next occurrence (the work: wish them well, think about a gift).

Google Tasks has no recurrence in the API, so the task covers the upcoming occurrence only,
while the calendar event repeats forever. That asymmetry is deliberate and documented.
"""

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)

TASK_SUFFIX = "złożyć życzenia, rozważyć prezent"
MARKER_RE = re.compile(r"⟦mstodo:([0-9a-f]{16})⟧")


def marker_for(ms_task_id: str) -> str:
    """Recovery marker (design: 'opcja A'). Lets a re-run find what a crashed run already wrote."""
    digest = hashlib.sha256(ms_task_id.encode()).hexdigest()[:16]
    return f"⟦mstodo:{digest}⟧"


def _parse_graph_datetime(raw: str) -> datetime | None:
    # Graph sends 7 fractional digits ("2026-10-17T00:00:00.0000000"); fromisoformat takes at most 6.
    cleaned = re.sub(r"(\.\d{6})\d+", r"\1", raw.strip()).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        logger.warning("Nie rozpoznano daty z Graph: %r", raw)
        return None


def due_date_of(task: dict[str, Any]) -> date | None:
    """Calendar date of a To Do due date, read **in its own time zone**.

    Converting through UTC can move the day by one, which would silently shift a birthday.
    """
    due = task.get("dueDateTime") or {}
    raw = due.get("dateTime")
    if not raw:
        return None
    moment = _parse_graph_datetime(raw)
    if moment is None:
        return None
    if moment.tzinfo is None:
        # Naive value is already expressed in due["timeZone"]; the date is what it says.
        return moment.date()
    zone_name = due.get("timeZone") or "UTC"
    try:
        zone = ZoneInfo(zone_name)
    except (ZoneInfoNotFoundError, ValueError):
        # Graph may send Windows zone names ("Central European Standard Time"); don't guess.
        logger.warning("Nieznana strefa czasowa %r, używam wartości bez konwersji", zone_name)
        return moment.date()
    return moment.astimezone(zone).date()


def next_occurrence(anchor: date, today: date) -> date:
    """First anniversary of `anchor` falling on or after `today`."""
    if anchor >= today:
        return anchor
    for year in range(today.year, today.year + 9):
        try:
            candidate = anchor.replace(year=year)
        except ValueError:
            # 29 February in a common year: RRULE:FREQ=YEARLY skips it too.
            continue
        if candidate >= today:
            return candidate
    return anchor


@dataclass(frozen=True)
class Occasion:
    """One yearly occasion derived from a Microsoft To Do task."""

    ms_task_id: str
    ms_list_id: str
    title: str
    anchor: date
    body: str = ""

    @property
    def marker(self) -> str:
        return marker_for(self.ms_task_id)

    @property
    def is_leap_day(self) -> bool:
        return (self.anchor.month, self.anchor.day) == (2, 29)

    def content_hash(self) -> str:
        payload = f"{self.title}|{self.anchor.isoformat()}|{self.body}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def warnings(self) -> list[str]:
        out = []
        if self.is_leap_day:
            out.append("29 lutego — wydarzenie wypadnie tylko w latach przestępnych")
        return out

    # --- Google payloads --------------------------------------------------

    def event_body(self) -> dict[str, Any]:
        """All-day yearly event. End date is exclusive in the Google Calendar API."""
        description = "\n\n".join(part for part in (self.body.strip(), self.marker) if part)
        return {
            "summary": self.title,
            "start": {"date": self.anchor.isoformat()},
            "end": {"date": (self.anchor + timedelta(days=1)).isoformat()},
            "recurrence": ["RRULE:FREQ=YEARLY"],
            # Free, not busy: an anniversary should not make the day look booked.
            "transparency": "transparent",
            "description": description,
        }

    def task_body(self, today: date) -> dict[str, Any]:
        """Google task for the upcoming occurrence. `due` carries a date; the API drops any time."""
        when = next_occurrence(self.anchor, today)
        notes = "\n\n".join(
            part
            for part in (self.body.strip(), f"Rocznica: {self.anchor.strftime('%d.%m')}", self.marker)
            if part
        )
        return {
            "title": f"{self.title} — {TASK_SUFFIX}",
            "notes": notes,
            "due": f"{when.isoformat()}T00:00:00.000Z",
        }


def occasion_from_task(task: dict[str, Any], ms_list_id: str) -> Occasion | None:
    """Build an Occasion, or None when the task carries no due date to anchor it to."""
    anchor = due_date_of(task)
    if anchor is None:
        return None
    title = (task.get("title") or "").strip()
    if not title:
        return None
    body = ""
    content = task.get("body") or {}
    if content.get("contentType") == "text":
        body = (content.get("content") or "").strip()
    return Occasion(
        ms_task_id=str(task["id"]),
        ms_list_id=ms_list_id,
        title=title,
        anchor=anchor,
        body=body,
    )
