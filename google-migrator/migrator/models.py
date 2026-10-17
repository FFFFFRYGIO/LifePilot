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
