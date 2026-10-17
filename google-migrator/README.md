# MS To Do → Google Tasks Migrator

Self-hosted Django service for a **one-shot, supervised** migration of Microsoft To Do (personal
account) into Google Tasks. Microsoft To Do is only ever read, never modified.

- Specification: [start_project.md](start_project.md)
- Design (schema, field mapping, lossy fields, idempotency): [docs/design.md](docs/design.md)

## Status

| Stage | Scope | State |
|---|---|---|
| 1 | Skeleton, OAuth (Microsoft + Google), Connections screen, list fetch | done |
| 2 | Staging of MS tasks, Settings, list mapping, dry-run Preview | – |
| 3 | Idempotent transfer, worker, Run screen | – |
| 4 | Exceptions queue | – |
| 5 | Wrap-up: verification report, marker cleanup | – |
| 6 | History, audit, remaining tests | – |
| + | Birthdays: yearly occasions to Google Calendar + Tasks (`migrate_birthdays`) | done |

## Birthdays and yearly occasions

`migrate_birthdays` moves one To Do list of yearly occasions (birthdays, name days, Mother's Day …)
into Google. Each source task becomes **two** things:

- a repeating **all-day calendar event** (`RRULE:FREQ=YEARLY`, shown as free, not busy) in a
  dedicated calendar, optionally shared with other accounts;
- a **Google task** for the next occurrence, titled "… — złożyć życzenia, rozważyć prezent", so the
  date is not just marked but actionable.

```sh
make dev                                        # or: docker compose --profile app up
uv run python manage.py migrate_birthdays --dry-run
uv run python manage.py migrate_birthdays
```

Options: `--source-list`, `--calendar`, `--share-with a@b.com c@d.com`, `--no-tasks`. Defaults come
from `BIRTHDAY_*` in `.env` (see `.env.example`). The calendar and the Google task list are created
only if missing, and sharing is re-applied idempotently.

**Google Tasks has no recurrence in the API.** The calendar event repeats forever; the task covers
the upcoming occurrence only. Re-running the command after a year creates the next task — the
calendar side needs nothing.

`BirthdayMapping` keeps one row per source task, so nothing is transferred twice. If a run dies
between the Google call and the commit, the next run finds its own `⟦mstodo:…⟧` marker in the event
description and adopts it instead of creating a duplicate.

## Verified API behaviour

**Google Tasks `due` stores the date only.** From the API reference (checked 2026-09-18):
*“Only date information is recorded; the time portion of the timestamp is discarded when setting
this field. It isn't possible to read or write the time that a task is scheduled for using the API.”*

Consequence: an MS `dueDateTime` is converted to a calendar date **in its own `timeZone`** (not
via UTC, which could shift the day) and sent as `YYYY-MM-DDT00:00:00.000Z`. The time of day is lost.
See [docs/design.md](docs/design.md) for the full list of lossy fields.

## Setup

Requirements: [uv](https://docs.astral.sh/uv/), Docker (for PostgreSQL), GNU Make
(on Windows: `winget install ezwinports.make`).

```sh
make install                    # uv sync + git hooks
cp .env.example .env            # then fill in the values, see below
make superuser                  # after `make db migrate`: login for the web UI
make dev                        # db + migrate + CSS + server on http://localhost:8000
```

`make help` lists all targets (`test`, `lint`, `fmt`, `typecheck`, `check`, `docker-up`, …).

Generate `TOKEN_ENCRYPTION_KEY` with
`uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
OAuth tokens are Fernet-encrypted in the database. The key only lives in the environment; to rotate,
put the new key first: `TOKEN_ENCRYPTION_KEY=new,old`.

### Microsoft (Entra ID)

1. Entra admin center → App registrations → New registration.
2. Supported account types: **Personal Microsoft accounts only**.
3. Redirect URI, platform **Web**: `{BASE_URL}/oauth/microsoft/callback`
   (e.g. `http://localhost:8000/oauth/microsoft/callback`).
4. Certificates & secrets → new client secret → `MS_CLIENT_SECRET`; the Application (client) ID → `MS_CLIENT_ID`.
5. API permissions → Microsoft Graph → Delegated: `Tasks.Read`, `User.Read` (and `offline_access`).
   **Do not** add `Tasks.ReadWrite`: the app is read-only on the Microsoft side by design.

### Google Cloud

1. Create a project, enable **Google Tasks API**.
2. OAuth consent screen: External, add yourself as a test user, scope `.../auth/tasks`.
3. Credentials → OAuth client ID → **Web application**, redirect URI `{BASE_URL}/oauth/google/callback`.
4. Copy the client ID and secret to `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`.

While the consent screen is in *Testing*, Google refresh tokens expire after 7 days. That is enough
for a one-shot migration. If one expires, the Connections screen shows it and you just reconnect.

## Development

```sh
make hooks                           # installs pre-commit and pre-push hooks
make test                            # needs `make db`
make lint typecheck
```

Hooks: ruff (lint + format), mypy (strict, django-stubs), `makemigrations --check` on commit;
the test suite runs on push.

> On Windows machines with Application Control, the generated `.venv/Scripts/pytest.exe` shim
> may be blocked; `python -m pytest` avoids it.

## Docker

```sh
docker compose --profile app up --build   # db + web on http://localhost:8000
```
