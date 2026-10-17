from datetime import timedelta

import pytest
import respx
from django.utils import timezone

from migrator.models import Connection, Provider


@pytest.fixture
def respx_mock():
    # Any request not explicitly mocked fails the test: no accidental real network calls.
    with respx.mock(assert_all_called=False, assert_all_mocked=True) as mock:
        yield mock


@pytest.fixture
def no_sleep(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr("migrator.http.time.sleep", slept.append)
    return slept


def make_connection(
    provider: Provider, *, expires_in: timedelta = timedelta(hours=1), **kwargs
) -> Connection:
    defaults = {
        "account_email": f"me@{provider.value}.example",
        "access_token": f"{provider.value}-access",
        "refresh_token": f"{provider.value}-refresh",
        "expires_at": timezone.now() + expires_in,
    }
    defaults.update(kwargs)
    return Connection.objects.create(provider=provider, **defaults)


@pytest.fixture
def ms_connection(db):
    return make_connection(Provider.MICROSOFT)


@pytest.fixture
def google_connection(db):
    return make_connection(Provider.GOOGLE)


@pytest.fixture
def user_client(client, django_user_model):
    user = django_user_model.objects.create_user("owner", password="pw")
    client.force_login(user)
    return client
