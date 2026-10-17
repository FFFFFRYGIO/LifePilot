from datetime import timedelta

from django.db import models
from django.utils import timezone

from .crypto import EncryptedTextField


class Provider(models.TextChoices):
    MICROSOFT = "microsoft", "Microsoft To Do"
    GOOGLE = "google", "Google Tasks"


class Connection(models.Model):
    class Status(models.TextChoices):
        OK = "ok", "Połączono"
        REAUTH_REQUIRED = "reauth_required", "Wymaga ponownego połączenia"

    provider = models.CharField(max_length=16, choices=Provider.choices, unique=True)
    account_email = models.CharField(max_length=320, blank=True)
    access_token = EncryptedTextField()
    refresh_token = EncryptedTextField(blank=True)
    expires_at = models.DateTimeField()
    scopes = models.TextField(blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.OK)
    last_error = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.get_provider_display()} ({self.account_email or '?'})"

    def expires_within(self, delta: timedelta) -> bool:
        return self.expires_at <= timezone.now() + delta


class BirthdayMapping(models.Model):
    """Idempotency for the birthdays feature: one row per source task, created at most once.

    `content_hash` records what was written, so a re-run can tell "already done" from "changed
    in To Do since". `recovery_marker` is the needle the reconciler looks for in Google when a
    run died between the API call and the commit.
    """

    class Status(models.TextChoices):
        DONE = "done", "Przeniesione"
        FAILED = "failed", "Błąd"

    ms_task_id = models.CharField(max_length=512, unique=True)
    ms_list_id = models.CharField(max_length=512)
    title = models.CharField(max_length=512)
    anchor_date = models.DateField()
    content_hash = models.CharField(max_length=64)
    recovery_marker = models.CharField(max_length=64, db_index=True)

    google_calendar_id = models.CharField(max_length=512, blank=True)
    google_event_id = models.CharField(max_length=512, blank=True)
    google_tasklist_id = models.CharField(max_length=512, blank=True)
    google_task_id = models.CharField(max_length=512, blank=True)

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DONE)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("anchor_date", "title")

    def __str__(self) -> str:
        return f"{self.title} ({self.anchor_date:%d.%m})"
