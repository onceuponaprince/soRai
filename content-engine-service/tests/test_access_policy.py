import json

import pytest

from content_engine_service.access_policy import Actor, AccessPolicy, AccessPolicyError, ProfileAccessDenied


INSTALLED = ["build-in-public", "general"]


def test_default_policy_allows_public_general_only():
    policy = AccessPolicy.default()
    actor = Actor.from_roles([])

    assert policy.allowed_profiles(actor, INSTALLED) == ("general",)
    assert policy.can_access(actor, "general", INSTALLED)
    assert not policy.can_access(actor, "build-in-public", INSTALLED)


def test_default_policy_allows_approver_inbox_profile():
    policy = AccessPolicy.default()
    actor = Actor.from_roles(["approver"])

    assert policy.allowed_profiles(actor, INSTALLED) == ("build-in-public", "general")


def test_default_policy_admin_wildcard_allows_all_installed_profiles():
    policy = AccessPolicy.default()
    actor = Actor.from_roles(["admin"])

    assert policy.allowed_profiles(actor, INSTALLED) == ("build-in-public", "general")


def test_policy_raises_for_denied_profile():
    policy = AccessPolicy.default()

    with pytest.raises(ProfileAccessDenied):
        policy.assert_can_access(Actor.from_roles(["operator"]), "build-in-public", INSTALLED)


def test_policy_loads_json_allowlist(tmp_path):
    path = tmp_path / "allowlists.json"
    path.write_text(json.dumps({"operator": ["build-in-public"]}))

    policy = AccessPolicy.from_json_file(path)

    assert policy.allowed_profiles(Actor.from_roles(["operator"]), INSTALLED) == ("build-in-public",)


def test_policy_rejects_malformed_json_shape(tmp_path):
    path = tmp_path / "allowlists.json"
    path.write_text(json.dumps({"operator": "general"}))

    with pytest.raises(AccessPolicyError):
        AccessPolicy.from_json_file(path)
