"""Encryption at rest for OAuth tokens. Keys live in the environment, never in the database."""

from functools import cache
from typing import Any

from cryptography.fernet import Fernet, MultiFernet
from django.conf import settings
from django.db import models


@cache
def _fernet() -> MultiFernet:
    keys = [k.strip() for k in settings.TOKEN_ENCRYPTION_KEYS if k.strip()]
    if not keys:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is not set")
    return MultiFernet([Fernet(k.encode()) for k in keys])


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()


class EncryptedTextField(models.TextField):  # type: ignore[type-arg]
    """TextField that is transparently Fernet-encrypted in the database."""

    def from_db_value(self, value: str | None, expression: Any, connection: Any) -> str | None:
        if value is None or value == "":
            return value
        return decrypt(value)

    def get_prep_value(self, value: Any) -> Any:
        value = super().get_prep_value(value)
        if value is None or value == "":
            return value
        return encrypt(value)
