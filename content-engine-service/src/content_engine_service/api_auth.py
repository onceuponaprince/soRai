from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from content_engine_service.access_policy import Actor


class ApiAuthError(PermissionError):
    """Raised when API-key authentication fails."""


@dataclass(frozen=True)
class ApiKeyAuthenticator:
    key_roles: dict[str, tuple[str, ...]]

    @classmethod
    def from_json_file(cls, path: str | Path) -> "ApiKeyAuthenticator":
        data = json.loads(Path(path).read_text())
        if not isinstance(data, dict):
            raise ValueError("api key file must be a JSON object")
        key_roles: dict[str, tuple[str, ...]] = {}
        for key, roles in data.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("api key entries must have non-empty string keys")
            if not isinstance(roles, list) or not all(isinstance(role, str) and role.strip() for role in roles):
                raise ValueError(f"api key {key!r} must map to a list of roles")
            key_roles[key.strip()] = tuple(sorted({role.strip().lower() for role in roles}))
        return cls(key_roles=key_roles)

    def authenticate(self, headers: dict[str, str]) -> Actor:
        key = (headers.get("x-api-key") or "").strip()
        if not key:
            raise ApiAuthError("missing x-api-key header")
        roles = self.key_roles.get(key)
        if roles is None:
            raise ApiAuthError("invalid api key")
        return Actor.from_roles(roles)
