from __future__ import annotations

import json

import pytest

from content_engine_service.api_auth import ApiAuthError, ApiKeyAuthenticator


def test_authenticator_from_json_file(tmp_path):
    path = tmp_path / "keys.json"
    path.write_text(json.dumps({"k1": ["operator"], "k2": ["approver", "admin"]}))

    auth = ApiKeyAuthenticator.from_json_file(path)
    assert auth.key_roles["k1"] == ("operator",)
    assert auth.key_roles["k2"] == ("admin", "approver")


def test_authenticator_accepts_valid_key():
    auth = ApiKeyAuthenticator(key_roles={"key": ("operator",)})
    actor = auth.authenticate({"x-api-key": "key"})
    assert actor.roles == ("operator",)


def test_authenticator_rejects_missing_key():
    auth = ApiKeyAuthenticator(key_roles={"key": ("operator",)})
    with pytest.raises(ApiAuthError):
        auth.authenticate({})


def test_authenticator_rejects_invalid_key():
    auth = ApiKeyAuthenticator(key_roles={"key": ("operator",)})
    with pytest.raises(ApiAuthError):
        auth.authenticate({"x-api-key": "bad"})
