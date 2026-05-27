from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROLE_OPERATOR = "operator"
ROLE_APPROVER = "approver"
ROLE_ADMIN = "admin"
PUBLIC_SCOPE = "public"
KNOWN_ROLES = frozenset({ROLE_OPERATOR, ROLE_APPROVER, ROLE_ADMIN})

DEFAULT_ALLOWLISTS: dict[str, tuple[str, ...]] = {
    PUBLIC_SCOPE: ("general",),
    ROLE_OPERATOR: ("general",),
    ROLE_APPROVER: ("general", "build-in-public"),
    ROLE_ADMIN: ("*",),
}


class AccessPolicyError(RuntimeError):
    """Raised when an allowlist file is malformed."""


class ProfileAccessDenied(PermissionError):
    """Raised when a role set cannot access a profile."""


@dataclass(frozen=True)
class Actor:
    roles: tuple[str, ...] = ()

    @classmethod
    def from_roles(cls, roles: Iterable[str] | None) -> "Actor":
        normalized = tuple(sorted({role.strip().lower() for role in roles or () if role.strip()}))
        return cls(roles=normalized)

    @property
    def scopes(self) -> tuple[str, ...]:
        return (PUBLIC_SCOPE, *self.roles)

    @property
    def is_admin(self) -> bool:
        return ROLE_ADMIN in self.roles


@dataclass(frozen=True)
class AccessPolicy:
    allowlists: dict[str, tuple[str, ...]]

    @classmethod
    def default(cls) -> "AccessPolicy":
        return cls(allowlists=dict(DEFAULT_ALLOWLISTS))

    @classmethod
    def from_json_file(cls, path: str | Path) -> "AccessPolicy":
        data = json.loads(Path(path).read_text())
        if not isinstance(data, dict):
            raise AccessPolicyError("allowlist file must contain a JSON object")
        allowlists: dict[str, tuple[str, ...]] = {}
        for scope, profiles in data.items():
            if not isinstance(scope, str) or not scope.strip():
                raise AccessPolicyError("allowlist scopes must be non-empty strings")
            if not isinstance(profiles, list) or not all(isinstance(item, str) and item.strip() for item in profiles):
                raise AccessPolicyError(f"allowlist scope {scope!r} must map to a list of profile names")
            allowlists[scope.strip().lower()] = tuple(item.strip() for item in profiles)
        return cls(allowlists=allowlists)

    def allowed_profiles(self, actor: Actor, installed_profiles: Iterable[str]) -> tuple[str, ...]:
        installed = tuple(sorted(set(installed_profiles)))
        if actor.is_admin and "*" in self.allowlists.get(ROLE_ADMIN, ("*",)):
            return installed

        allowed: set[str] = set()
        for scope in actor.scopes:
            for profile in self.allowlists.get(scope, ()): 
                if profile == "*":
                    allowed.update(installed)
                elif profile in installed:
                    allowed.add(profile)
        return tuple(sorted(allowed))

    def can_access(self, actor: Actor, profile: str, installed_profiles: Iterable[str]) -> bool:
        return profile in self.allowed_profiles(actor, installed_profiles)

    def assert_can_access(self, actor: Actor, profile: str, installed_profiles: Iterable[str]) -> None:
        if not self.can_access(actor, profile, installed_profiles):
            roles = ",".join(actor.roles) or PUBLIC_SCOPE
            raise ProfileAccessDenied(f"profile {profile!r} is not allowed for roles: {roles}")
