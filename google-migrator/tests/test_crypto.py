import pytest
from cryptography.fernet import Fernet
from django.db import connection as db_connection
from django.test import override_settings

from migrator import crypto
from migrator.models import Provider
from tests.conftest import make_connection


@pytest.fixture(autouse=True)
def _reset_key_cache():
    crypto._fernet.cache_clear()
    yield
    crypto._fernet.cache_clear()


@pytest.mark.django_db
def test_tokens_are_encrypted_at_rest():
    conn = make_connection(Provider.GOOGLE, access_token="secret-access", refresh_token="secret-refresh")

    with db_connection.cursor() as cur:
        cur.execute("SELECT access_token, refresh_token FROM migrator_connection WHERE id = %s", [conn.pk])
        raw_access, raw_refresh = cur.fetchone()

    assert "secret" not in raw_access
    assert "secret" not in raw_refresh
    conn.refresh_from_db()
    assert conn.access_token == "secret-access"
    assert conn.refresh_token == "secret-refresh"


def test_key_rotation_decrypts_with_old_key():
    old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    with override_settings(TOKEN_ENCRYPTION_KEYS=[old]):
        crypto._fernet.cache_clear()
        token = crypto.encrypt("value")
    with override_settings(TOKEN_ENCRYPTION_KEYS=[new, old]):
        crypto._fernet.cache_clear()
        assert crypto.decrypt(token) == "value"


def test_missing_key_fails_loudly():
    with override_settings(TOKEN_ENCRYPTION_KEYS=[""]), pytest.raises(RuntimeError):
        crypto.encrypt("x")
