from __future__ import annotations

import pytest


django = pytest.importorskip("django")

from django.test import Client
from django.test.utils import override_settings


@pytest.mark.django_db
@override_settings(
    SORAI_MOCK_OUTPUT="bridge mock",
    SORAI_STORE_PATH="/tmp/sorai-django-bridge.sqlite3",
)
def test_health_endpoint():
    client = Client()
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
@override_settings(
    SORAI_MOCK_OUTPUT="bridge mock",
    SORAI_STORE_PATH="/tmp/sorai-django-bridge.sqlite3",
)
def test_profiles_endpoint():
    client = Client()
    response = client.get("/api/v1/profiles", {"role": "approver"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["profiles"] == ["build-in-public", "general"]
