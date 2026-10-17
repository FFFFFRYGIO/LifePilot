"""Django settings. All secrets and deployment-specific values come from the environment."""

from pathlib import Path

import django_stubs_ext
import environ

django_stubs_ext.monkeypatch()

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CSRF_TRUSTED_ORIGINS=(list, []),
)
environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

# Public base URL of this service; OAuth redirect URIs are derived from it and must match
# exactly what is registered in Entra ID and Google Cloud Console.
BASE_URL = env("BASE_URL", default="http://localhost:8000").rstrip("/")

# Fernet key(s) for OAuth tokens at rest. Comma-separated; the first one encrypts,
# all of them decrypt (key rotation). Never stored in the database.
TOKEN_ENCRYPTION_KEYS = env.list("TOKEN_ENCRYPTION_KEY")

MS_CLIENT_ID = env("MS_CLIENT_ID", default="")
MS_CLIENT_SECRET = env("MS_CLIENT_SECRET", default="")
# Personal Microsoft accounts only.
MS_AUTHORITY = env("MS_AUTHORITY", default="https://login.microsoftonline.com/consumers")

GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET", default="")

# --- birthdays feature ------------------------------------------------------
# Yearly occasions move from one To Do list into one Google calendar plus a matching task list.
BIRTHDAY_SOURCE_LIST = env("BIRTHDAY_SOURCE_LIST", default="Urodziny")
BIRTHDAY_CALENDAR_NAME = env("BIRTHDAY_CALENDAR_NAME", default="Urodziny")
BIRTHDAY_SHARE_WITH = env.list("BIRTHDAY_SHARE_WITH", default=[])
BIRTHDAY_SHARE_ROLE = env("BIRTHDAY_SHARE_ROLE", default="writer")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django_tailwind_cli",
    "migrator",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = 60
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "migrator:connections"
LOGOUT_REDIRECT_URL = "login"

LANGUAGE_CODE = "pl"
TIME_ZONE = env("TIME_ZONE", default="Europe/Warsaw")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "assets"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

TAILWIND_CLI_SRC_CSS = "frontend/source.css"
TAILWIND_CLI_DIST_CSS = "css/tailwind.css"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = BASE_URL.startswith("https://")
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
