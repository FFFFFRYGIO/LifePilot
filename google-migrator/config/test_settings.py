"""Settings for the test suite: fixed secrets, Postgres from `docker compose up -d db`."""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("TOKEN_ENCRYPTION_KEY", "VGVzdEtleVRlc3RLZXlUZXN0S2V5VGVzdEtleTEyMzQ=")
os.environ.setdefault("DATABASE_URL", "postgres://migrator:migrator@localhost:55433/migrator")
os.environ.setdefault("BASE_URL", "http://testserver")
os.environ.setdefault("MS_CLIENT_ID", "ms-client")
os.environ.setdefault("MS_CLIENT_SECRET", "ms-secret")
os.environ.setdefault("GOOGLE_CLIENT_ID", "g-client")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "g-secret")

from .settings import *  # noqa: F403

STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.StaticFilesStorage"  # noqa: F405
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m]  # noqa: F405
