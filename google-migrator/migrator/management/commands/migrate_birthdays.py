"""Move yearly occasions (birthdays, name days, …) from Microsoft To Do to Google.

Each source task becomes a repeating all-day event in a dedicated calendar and a Google task
for the next occurrence. Microsoft To Do is only read. `--dry-run` writes nothing to Google.
"""

import logging
from argparse import ArgumentParser
from datetime import date
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ...birthdays import Occasion, occasion_from_task
from ...clients.gcal import GoogleCalendarClient
from ...clients.graph import GraphClient
from ...clients.gtasks import GoogleTasksClient
from ...models import BirthdayMapping

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Przenosi urodziny i rocznice z Microsoft To Do do Google Calendar i Google Tasks."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Pokaż plan bez żadnego zapisu do Google (nic nie jest tworzone ani zmieniane).",
        )
        parser.add_argument(
            "--source-list",
            default=settings.BIRTHDAY_SOURCE_LIST,
            help="Nazwa listy w Microsoft To Do, z której czytamy.",
        )
        parser.add_argument(
            "--calendar",
            default=settings.BIRTHDAY_CALENDAR_NAME,
            help="Nazwa kalendarza Google (zostanie utworzony, jeśli nie istnieje).",
        )
        parser.add_argument(
            "--share-with",
            nargs="*",
            default=list(settings.BIRTHDAY_SHARE_WITH),
            help="Adresy e-mail, którym udostępnić kalendarz.",
        )
        parser.add_argument(
            "--no-tasks",
            action="store_true",
            help="Twórz tylko wydarzenia w kalendarzu, bez zadań w Google Tasks.",
        )

    # --- helpers ----------------------------------------------------------

    def _read_source(self, source_list: str) -> tuple[str, list[Occasion]]:
        with GraphClient() as graph:
            ms_list = graph.find_task_list_by_name(source_list)
            if ms_list is None:
                raise CommandError(f"Nie ma listy {source_list!r} w Microsoft To Do.")
            raw_tasks = graph.list_tasks(ms_list["id"])

        occasions, skipped = [], []
        for task in raw_tasks:
            occasion = occasion_from_task(task, ms_list["id"])
            if occasion is None:
                skipped.append(task.get("title") or task.get("id"))
            else:
                occasions.append(occasion)
        if skipped:
            self.stdout.write(self.style.WARNING(f"Pominięte (brak daty): {len(skipped)}"))
            for title in skipped:
                self.stdout.write(f"  - {title}")
        occasions.sort(key=lambda o: (o.anchor.month, o.anchor.day, o.title))
        return ms_list["id"], occasions

    def _ensure_calendar(self, gcal: GoogleCalendarClient, name: str, *, dry_run: bool) -> str | None:
        existing = gcal.find_calendar_by_summary(name)
        if existing is not None:
            self.stdout.write(f"Kalendarz {name!r}: istnieje ({existing['id']})")
            return str(existing["id"])
        if dry_run:
            self.stdout.write(self.style.WARNING(f"Kalendarz {name!r}: zostałby utworzony"))
            return None
        created = gcal.create_calendar(
            name,
            time_zone=settings.TIME_ZONE,
            description="Urodziny i rocznice przeniesione z Microsoft To Do.",
        )
        self.stdout.write(self.style.SUCCESS(f"Kalendarz {name!r}: utworzony ({created['id']})"))
        return str(created["id"])

    def _ensure_sharing(
        self, gcal: GoogleCalendarClient, calendar_id: str | None, emails: list[str], *, dry_run: bool
    ) -> None:
        for email in emails:
            if dry_run or calendar_id is None:
                self.stdout.write(self.style.WARNING(f"Udostępnienie {email}: zostałoby nadane"))
                continue
            gcal.share_with(calendar_id, email, role=settings.BIRTHDAY_SHARE_ROLE)
            self.stdout.write(self.style.SUCCESS(f"Udostępnione: {email}"))

    def _ensure_task_list(self, gtasks: GoogleTasksClient, name: str, *, dry_run: bool) -> str | None:
        existing = gtasks.find_task_list_by_title(name)
        if existing is not None:
            self.stdout.write(f"Lista zadań {name!r}: istnieje ({existing['id']})")
            return str(existing["id"])
        if dry_run:
            self.stdout.write(self.style.WARNING(f"Lista zadań {name!r}: zostałaby utworzona"))
            return None
        created = gtasks.create_task_list(name)
        self.stdout.write(self.style.SUCCESS(f"Lista zadań {name!r}: utworzona ({created['id']})"))
        return str(created["id"])

    # --- main -------------------------------------------------------------

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]
        today: date = timezone.localdate()

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN — nic nie zostanie zapisane w Google.\n"))

        ms_list_id, occasions = self._read_source(options["source_list"])
        self.stdout.write(f"Do przeniesienia z {options['source_list']!r}: {len(occasions)}\n")

        done = {
            m.ms_task_id: m
            for m in BirthdayMapping.objects.filter(ms_list_id=ms_list_id, status=BirthdayMapping.Status.DONE)
        }

        with GoogleCalendarClient() as gcal, GoogleTasksClient() as gtasks:
            calendar_id = self._ensure_calendar(gcal, options["calendar"], dry_run=dry_run)
            self._ensure_sharing(gcal, calendar_id, options["share_with"], dry_run=dry_run)
            task_list_id = (
                None
                if options["no_tasks"]
                else self._ensure_task_list(gtasks, options["calendar"], dry_run=dry_run)
            )
            self.stdout.write("")

            created = skipped = failed = 0
            for occasion in occasions:
                label = f"{occasion.anchor:%d.%m}  {occasion.title}"
                for warning in occasion.warnings():
                    self.stdout.write(self.style.WARNING(f"  ! {label}: {warning}"))

                previous = done.get(occasion.ms_task_id)
                if previous is not None and previous.content_hash == occasion.content_hash():
                    skipped += 1
                    continue

                if dry_run:
                    self.stdout.write(f"  + {label}")
                    created += 1
                    continue

                try:
                    self._transfer(gcal, gtasks, occasion, calendar_id, task_list_id, today)
                except Exception as exc:
                    failed += 1
                    logger.exception("Nie udało się przenieść %s", occasion.title)
                    BirthdayMapping.objects.update_or_create(
                        ms_task_id=occasion.ms_task_id,
                        defaults={
                            "ms_list_id": occasion.ms_list_id,
                            "title": occasion.title,
                            "anchor_date": occasion.anchor,
                            "content_hash": occasion.content_hash(),
                            "recovery_marker": occasion.marker,
                            "status": BirthdayMapping.Status.FAILED,
                            "last_error": str(exc)[:1000],
                        },
                    )
                    self.stdout.write(self.style.ERROR(f"  x {label}: {exc}"))
                else:
                    created += 1
                    self.stdout.write(self.style.SUCCESS(f"  + {label}"))

        verb = "do przeniesienia" if dry_run else "przeniesione"
        self.stdout.write(f"\n{verb}: {created}, bez zmian: {skipped}, błędy: {failed}")

    def _transfer(
        self,
        gcal: GoogleCalendarClient,
        gtasks: GoogleTasksClient,
        occasion: Occasion,
        calendar_id: str | None,
        task_list_id: str | None,
        today: date,
    ) -> None:
        if calendar_id is None:
            raise CommandError("Brak kalendarza docelowego.")

        # Reconcile before writing: a previous run may have created this and died before committing.
        existing = [
            event
            for event in gcal.search_events(calendar_id, occasion.marker)
            if occasion.marker in (event.get("description") or "")
        ]
        event = existing[0] if existing else gcal.create_event(calendar_id, occasion.event_body())

        task_id = ""
        if task_list_id is not None:
            known = [
                task
                for task in gtasks.list_tasks(task_list_id)
                if occasion.marker in (task.get("notes") or "")
            ]
            task = (
                known[0]
                if known
                else gtasks.create_task(task_list_id, occasion.task_body(timezone.localdate()))
            )
            task_id = str(task["id"])

        BirthdayMapping.objects.update_or_create(
            ms_task_id=occasion.ms_task_id,
            defaults={
                "ms_list_id": occasion.ms_list_id,
                "title": occasion.title,
                "anchor_date": occasion.anchor,
                "content_hash": occasion.content_hash(),
                "recovery_marker": occasion.marker,
                "google_calendar_id": calendar_id,
                "google_event_id": str(event["id"]),
                "google_tasklist_id": task_list_id or "",
                "google_task_id": task_id,
                "status": BirthdayMapping.Status.DONE,
                "last_error": "",
                "last_synced_at": timezone.now(),
            },
        )
