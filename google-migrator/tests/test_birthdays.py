from datetime import date
from typing import Any

import httpx
import pytest
import respx
from django.core.management import call_command

from migrator.birthdays import (
    Occasion,
    due_date_of,
    marker_for,
    next_occurrence,
    occasion_from_task,
)
from migrator.models import BirthdayMapping

GRAPH = "https://graph.microsoft.com/v1.0"
TASKS = "https://tasks.googleapis.com/tasks/v1"
CAL = "https://www.googleapis.com/calendar/v3"

MS_LIST_ID = "ms-list-1"
CAL_ID = "cal-urodziny"
TASKLIST_ID = "tl-urodziny"


def ms_task(task_id: str, title: str, due: str, zone: str = "UTC") -> dict[str, Any]:
    return {
        "id": task_id,
        "title": title,
        "status": "notStarted",
        "dueDateTime": {"dateTime": due, "timeZone": zone},
    }


# --- field mapping ----------------------------------------------------------


def test_due_date_is_read_in_its_own_timezone_not_via_utc():
    """Midnight in Warsaw is the previous day in UTC; the date must not slip."""
    task = ms_task("1", "Urodziny Kasi", "2026-10-17T00:00:00.0000000", "Europe/Warsaw")
    assert due_date_of(task) == date(2026, 10, 17)


def test_due_date_handles_graph_seven_digit_fraction():
    assert due_date_of(ms_task("1", "x", "2027-03-12T00:00:00.0000000")) == date(2027, 3, 12)


def test_due_date_of_task_without_due_is_none():
    assert due_date_of({"id": "1", "title": "x"}) is None


def test_unknown_windows_timezone_falls_back_without_shifting_the_day():
    task = ms_task("1", "x", "2027-01-03T00:00:00.0000000", "Central European Standard Time")
    assert due_date_of(task) == date(2027, 1, 3)


def test_occasion_from_task_without_due_date_is_skipped():
    assert occasion_from_task({"id": "1", "title": "Bez daty"}, MS_LIST_ID) is None


@pytest.mark.parametrize(
    ("anchor", "today", "expected"),
    [
        (date(2027, 3, 12), date(2026, 10, 17), date(2027, 3, 12)),  # already ahead
        (date(2026, 10, 11), date(2026, 10, 17), date(2027, 10, 11)),  # overdue -> next year
        (date(2026, 10, 17), date(2026, 10, 17), date(2026, 10, 17)),  # today counts
        (date(2024, 2, 29), date(2026, 10, 17), date(2028, 2, 29)),  # leap day skips to leap year
    ],
)
def test_next_occurrence(anchor, today, expected):
    assert next_occurrence(anchor, today) == expected


def test_event_body_is_all_day_yearly_and_carries_the_marker():
    occasion = Occasion("task-1", MS_LIST_ID, "Urodziny Kasi Wach", date(2026, 10, 17))
    body = occasion.event_body()
    assert body["start"] == {"date": "2026-10-17"}
    assert body["end"] == {"date": "2026-10-18"}  # exclusive end
    assert body["recurrence"] == ["RRULE:FREQ=YEARLY"]
    assert body["transparency"] == "transparent"
    assert marker_for("task-1") in body["description"]


def test_task_body_targets_the_next_occurrence_and_names_the_work():
    occasion = Occasion("task-1", MS_LIST_ID, "Urodziny Kasi Wach", date(2026, 10, 11))
    body = occasion.task_body(today=date(2026, 10, 17))
    assert body["due"] == "2027-10-11T00:00:00.000Z"
    assert "złożyć życzenia" in body["title"]
    assert marker_for("task-1") in body["notes"]


def test_leap_day_occasion_warns():
    occasion = Occasion("task-1", MS_LIST_ID, "Urodziny Marty", date(2024, 2, 29))
    assert occasion.warnings()


# --- command ----------------------------------------------------------------


@pytest.fixture
def source_list(respx_mock):
    respx_mock.get(f"{GRAPH}/me/todo/lists").mock(
        return_value=httpx.Response(200, json={"value": [{"id": MS_LIST_ID, "displayName": "Urodziny"}]})
    )
    respx_mock.get(f"{GRAPH}/me/todo/lists/{MS_LIST_ID}/tasks").mock(
        return_value=httpx.Response(
            200,
            json={
                "value": [
                    ms_task("t1", "Urodziny Kasi Wach", "2026-10-17T00:00:00.0000000"),
                    ms_task("t2", "Urodziny taty", "2026-10-31T00:00:00.0000000"),
                ]
            },
        )
    )
    return respx_mock


def mock_google_targets(
    respx_mock: respx.MockRouter, *, calendar_exists: bool = True, tasklist_exists: bool = True
) -> None:
    calendars = [{"id": CAL_ID, "summary": "Urodziny"}] if calendar_exists else []
    respx_mock.get(f"{CAL}/users/me/calendarList").mock(
        return_value=httpx.Response(200, json={"items": calendars})
    )
    lists = [{"id": TASKLIST_ID, "title": "Urodziny"}] if tasklist_exists else []
    respx_mock.get(f"{TASKS}/users/@me/lists").mock(return_value=httpx.Response(200, json={"items": lists}))
    respx_mock.get(f"{CAL}/calendars/{CAL_ID}/acl").mock(return_value=httpx.Response(200, json={"items": []}))


def test_dry_run_writes_nothing_to_google(source_list, ms_connection, google_connection):
    """Hard requirement from the spec: a dry run performs no write against Google."""
    mock_google_targets(source_list, calendar_exists=False, tasklist_exists=False)

    call_command("migrate_birthdays", "--dry-run", "--share-with", "someone@example.com")

    writes = [c for c in source_list.calls if c.request.method != "GET"]
    assert writes == [], f"dry-run wykonał zapis: {[str(c.request.url) for c in writes]}"
    assert not BirthdayMapping.objects.exists()


def test_transfer_creates_event_and_task_per_occasion(source_list, ms_connection, google_connection):
    mock_google_targets(source_list)
    respx_mock = source_list
    respx_mock.get(f"{CAL}/calendars/{CAL_ID}/events").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    respx_mock.get(f"{TASKS}/lists/{TASKLIST_ID}/tasks").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    respx_mock.post(f"{CAL}/calendars/{CAL_ID}/events").mock(
        side_effect=[
            httpx.Response(200, json={"id": "ev-1"}),
            httpx.Response(200, json={"id": "ev-2"}),
        ]
    )
    respx_mock.post(f"{TASKS}/lists/{TASKLIST_ID}/tasks").mock(
        side_effect=[
            httpx.Response(200, json={"id": "gt-1"}),
            httpx.Response(200, json={"id": "gt-2"}),
        ]
    )

    call_command("migrate_birthdays")

    assert BirthdayMapping.objects.count() == 2
    mapping = BirthdayMapping.objects.get(ms_task_id="t1")
    assert mapping.google_event_id == "ev-1"
    assert mapping.google_task_id == "gt-1"
    assert mapping.status == BirthdayMapping.Status.DONE


def test_second_run_is_idempotent(source_list, ms_connection, google_connection):
    """Nothing may be transferred twice: the second run creates no further events."""
    mock_google_targets(source_list)
    respx_mock = source_list
    respx_mock.get(f"{CAL}/calendars/{CAL_ID}/events").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    respx_mock.get(f"{TASKS}/lists/{TASKLIST_ID}/tasks").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    create_event = respx_mock.post(f"{CAL}/calendars/{CAL_ID}/events").mock(
        side_effect=[
            httpx.Response(200, json={"id": "ev-1"}),
            httpx.Response(200, json={"id": "ev-2"}),
        ]
    )
    respx_mock.post(f"{TASKS}/lists/{TASKLIST_ID}/tasks").mock(
        side_effect=[
            httpx.Response(200, json={"id": "gt-1"}),
            httpx.Response(200, json={"id": "gt-2"}),
        ]
    )

    call_command("migrate_birthdays")
    assert create_event.call_count == 2

    call_command("migrate_birthdays")
    assert create_event.call_count == 2, "drugi przebieg utworzył wydarzenia ponownie"
    assert BirthdayMapping.objects.count() == 2


def test_crashed_run_reconciles_by_marker_instead_of_duplicating(
    source_list, ms_connection, google_connection
):
    """Event already in Google but no mapping row: find it by marker, do not create a second one."""
    mock_google_targets(source_list)
    respx_mock = source_list
    marker = marker_for("t1")
    respx_mock.get(f"{CAL}/calendars/{CAL_ID}/events").mock(
        return_value=httpx.Response(
            200, json={"items": [{"id": "ev-existing", "description": f"...{marker}"}]}
        )
    )
    respx_mock.get(f"{TASKS}/lists/{TASKLIST_ID}/tasks").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    create_event = respx_mock.post(f"{CAL}/calendars/{CAL_ID}/events").mock(
        return_value=httpx.Response(200, json={"id": "ev-new"})
    )
    respx_mock.post(f"{TASKS}/lists/{TASKLIST_ID}/tasks").mock(
        side_effect=[
            httpx.Response(200, json={"id": "gt-1"}),
            httpx.Response(200, json={"id": "gt-2"}),
        ]
    )

    call_command("migrate_birthdays")

    # Only the second occasion needed a fresh event; the first was recovered by its marker.
    assert create_event.call_count == 1
    assert BirthdayMapping.objects.get(ms_task_id="t1").google_event_id == "ev-existing"


def test_microsoft_is_never_written_to(source_list, ms_connection, google_connection):
    mock_google_targets(source_list)
    respx_mock = source_list
    respx_mock.get(f"{CAL}/calendars/{CAL_ID}/events").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    respx_mock.get(f"{TASKS}/lists/{TASKLIST_ID}/tasks").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    respx_mock.post(f"{CAL}/calendars/{CAL_ID}/events").mock(
        side_effect=[httpx.Response(200, json={"id": "ev-1"}), httpx.Response(200, json={"id": "ev-2"})]
    )
    respx_mock.post(f"{TASKS}/lists/{TASKLIST_ID}/tasks").mock(
        side_effect=[httpx.Response(200, json={"id": "gt-1"}), httpx.Response(200, json={"id": "gt-2"})]
    )

    call_command("migrate_birthdays")

    graph_writes = [
        c
        for c in respx_mock.calls
        if "graph.microsoft.com" in str(c.request.url) and c.request.method != "GET"
    ]
    assert graph_writes == []
