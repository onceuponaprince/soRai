from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from wsgiref.simple_server import make_server

from content_engine_service import profiles_registry
from content_engine_service.access_policy import Actor, AccessPolicy, ProfileAccessDenied
from content_engine_service.api_auth import ApiAuthError, ApiKeyAuthenticator
from content_engine_service.boundary_validator import BoundaryRejected
from content_engine_service.lane_adapter import LaneDispatchError, LaneRequest, dispatch as lane_dispatch
from content_engine_service.run_pipeline import UnknownProfile, execute_pipeline
from content_engine_service.run_types import DispatchResult, RunMode
from content_engine_service.store import RunStore


@dataclass(frozen=True)
class ApiConfig:
    engine_root: Path
    artifact_root: Path
    policy: AccessPolicy
    store_path: Path | None = None
    runner: Path | None = None
    default_lane: str = "api"
    default_tool: str = "router-qwen3.6"
    timeout: int = 180
    mock_output: str = ""
    authenticator: ApiKeyAuthenticator | None = None


def create_wsgi_app(config: ApiConfig):
    def app(environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "")

        if method == "OPTIONS":
            start_response("204 No Content", [
                ("Content-Length", "0"),
                *_cors_headers(),
            ])
            return [b""]

        query = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=False)
        body = _read_json_body(environ)
        headers = _headers(environ)

        status, payload = handle_request(config=config, method=method, path=path, query=query, body=body, headers=headers)
        status_line = f"{status} {_reason_phrase(status)}"
        raw = json.dumps(payload).encode("utf-8")
        start_response(status_line, [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(raw))),
            *_cors_headers(),
        ])
        return [raw]

    return app


def serve(config: ApiConfig, host: str = "127.0.0.1", port: int = 8000) -> None:
    app = create_wsgi_app(config)
    with make_server(host, port, app) as server:
        server.serve_forever()


def handle_request(*, config: ApiConfig, method: str, path: str, query: dict[str, list[str]], body: dict[str, Any], headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
    try:
        actor = _resolve_actor(config=config, path=path, query=query, body=body, headers=headers)

        if method == "GET" and path == "/health":
            return 200, {"status": "ok"}

        if method == "GET" and path == "/api/v1/whoami":
            return 200, {"roles": list(actor.roles)}

        if method == "GET" and path == "/api/v1/profiles":
            names = profiles_registry.list_profile_names(config.engine_root)
            allowed = config.policy.allowed_profiles(actor, names)
            return 200, {"profiles": list(allowed), "roles": list(actor.roles)}

        if method == "GET" and path == "/api/v1/profiles/meta":
            names = profiles_registry.list_profile_names(config.engine_root)
            allowed = config.policy.allowed_profiles(actor, names)
            cache: dict[tuple[str, str, str], profiles_registry.RenderedBundle] = {}
            items = []
            for profile in allowed:
                bundle = profiles_registry.render_bundle(config.engine_root, profile, cache=cache)
                items.append(_profile_meta_view(bundle.profile))
            return 200, {"profiles": items, "roles": list(actor.roles)}

        if method == "POST" and path == "/api/v1/signup":
            store = _require_store(config)
            email = str(body.get("email", "")).strip()
            requested_roles = body.get("requested_roles", ["operator"])
            if not isinstance(requested_roles, list):
                return 400, {"error": "requested_roles must be a list"}
            signup = store.request_signup(
                email=email,
                requested_roles=tuple(str(role) for role in requested_roles),
            )
            return 201, {"signup": _signup_view(signup)}

        if method == "GET" and path == "/api/v1/signup/pending":
            if "admin" not in set(actor.roles):
                return 403, {"error": "pending signup review requires admin role"}
            store = _require_store(config)
            pending = [_signup_view(row) for row in store.list_signup_requests("pending")]
            return 200, {"pending": pending}

        if method == "POST" and path.startswith("/api/v1/signup/"):
            parts = [part for part in path.split("/") if part]
            if len(parts) != 5:
                return 404, {"error": "not found"}
            if "admin" not in set(actor.roles):
                return 403, {"error": "signup decisions require admin role"}

            try:
                signup_id = int(parts[3])
            except ValueError:
                return 400, {"error": "invalid signup id"}
            action = parts[4]
            if action not in {"approve", "reject"}:
                return 404, {"error": "not found"}

            store = _require_store(config)
            note = str(body.get("note", "")).strip()
            decided_by = ",".join(actor.roles) or "admin"

            if action == "approve":
                approved_roles = body.get("approved_roles", None)
                if approved_roles is not None and not isinstance(approved_roles, list):
                    return 400, {"error": "approved_roles must be a list"}
                signup = store.approve_signup(
                    signup_id=signup_id,
                    approved_by=decided_by,
                    approved_roles=tuple(str(role) for role in approved_roles) if approved_roles is not None else None,
                    note=note,
                )
                return 200, {"signup": _signup_view(signup), "api_key": signup["api_key"]}

            signup = store.reject_signup(signup_id=signup_id, decided_by=decided_by, note=note)
            return 200, {"signup": _signup_view(signup)}

        if method == "GET" and path == "/api/v1/admin/api-keys":
            if "admin" not in set(actor.roles):
                return 403, {"error": "admin role required"}
            store = _require_store(config)
            keys = [_issued_key_view(row) for row in store.list_issued_api_keys()]
            return 200, {"api_keys": keys}

        if method == "POST" and path.startswith("/api/v1/admin/api-keys/"):
            if "admin" not in set(actor.roles):
                return 403, {"error": "admin role required"}
            parts = [part for part in path.split("/") if part]
            if len(parts) != 6:
                return 404, {"error": "not found"}
            api_key = parts[4]
            action = parts[5]
            if action not in {"revoke", "reactivate"}:
                return 404, {"error": "not found"}
            store = _require_store(config)
            updated = store.set_api_key_active(api_key=api_key, is_active=(action == "reactivate"))
            return 200, {"api_key": _issued_key_view(updated)}

        if method == "POST" and path == "/api/v1/runs":
            profile = str(body.get("profile", "")).strip()
            brief = str(body.get("brief", "")).strip()
            if not profile:
                return 400, {"error": "profile is required"}
            if not brief:
                return 400, {"error": "brief is required"}

            names = profiles_registry.list_profile_names(config.engine_root)
            config.policy.assert_can_access(actor, profile, names)

            mode = RunMode(str(body.get("mode", RunMode.DRY_RUN.value)))
            lane = str(body.get("lane", config.default_lane))
            tool = str(body.get("tool", config.default_tool))
            timeout = int(body.get("timeout", config.timeout))

            request_mock = str(body.get("mock_output", "")).strip()
            effective_mock = request_mock or config.mock_output

            if effective_mock:
                dispatch_fn = lambda bundle, inputs: DispatchResult(output=effective_mock, receipt_id="mock")
            else:
                if config.runner is None:
                    return 400, {"error": "runner is required when mock_output is not provided"}

                def dispatch_fn(bundle: str, inputs: dict) -> DispatchResult:
                    return lane_dispatch(LaneRequest(bundle=bundle, inputs=inputs, lane=lane, tool=tool, provenance=f"api-run profile={profile}", runner=config.runner, timeout=timeout))

            store = RunStore(config.store_path) if config.store_path else None
            record = execute_pipeline(engine_root=config.engine_root, profile=profile, inputs={"brief": brief}, mode=mode, dispatch=dispatch_fn, artifact_root=config.artifact_root, store=store)
            return 201, _run_payload(record)

        if method == "GET" and path == "/api/v1/runs":
            store = _require_store(config)
            runs = store.list_runs()
            payload = []
            for run in runs:
                artifact = store.list_artifacts(run.id)
                approvals = store.list_approval_events(run.id)
                payload.append({
                    "run_id": run.id,
                    "profile": run.profile,
                    "mode": run.mode,
                    "receipt_id": run.receipt_id,
                    "boundary": {"status": run.boundary_status, "detail": run.boundary_detail},
                    "sink": run.sink,
                    "artifact": artifact[0] if artifact else None,
                    "approval": _approval_view(approvals[0]) if approvals else None,
                })
            return 200, {"runs": payload}

        if method == "GET" and path.startswith("/api/v1/runs/"):
            store = _require_store(config)
            run_id = path.rsplit("/", 1)[-1]
            run = store.get_run(run_id)
            if run is None:
                return 404, {"error": "run not found"}
            artifact = store.list_artifacts(run.id)
            approvals = store.list_approval_events(run.id)
            return 200, {
                "run_id": run.id,
                "profile": run.profile,
                "mode": run.mode,
                "receipt_id": run.receipt_id,
                "boundary": {"status": run.boundary_status, "detail": run.boundary_detail},
                "sink": run.sink,
                "artifact": artifact[0] if artifact else None,
                "approval": _approval_view(approvals[0]) if approvals else None,
            }

        if method == "POST" and path.startswith("/api/v1/approvals/"):
            parts = [part for part in path.split("/") if part]
            if len(parts) != 5:
                return 404, {"error": "not found"}
            event_id = parts[3]
            action = parts[4]
            if action not in {"approve", "reject"}:
                return 404, {"error": "not found"}

            if not ({"approver", "admin"} & set(actor.roles)):
                return 403, {"error": "approval decision requires approver or admin role"}

            store = _require_store(config)
            decision = "approved" if action == "approve" else "rejected"
            note = str(body.get("note", "")).strip()
            decided_by = ",".join(actor.roles) or "approver"
            updated = store.decide_approval(event_id=event_id, decision=decision, decided_by=decided_by, note=note)
            return 200, {"approval": _approval_view(updated)}

        if method == "GET" and path == "/api/v1/approvals":
            store = _require_store(config)
            approvals = [_approval_view(row) for row in store.list_approval_events(None)]
            return 200, {"approvals": approvals}

        return 404, {"error": "not found"}
    except ApiAuthError as exc:
        return 401, {"error": str(exc)}
    except ProfileAccessDenied as exc:
        return 403, {"error": str(exc)}
    except UnknownProfile as exc:
        return 400, {"error": str(exc)}
    except BoundaryRejected as exc:
        verdict = exc.verdict
        return 422, {"error": "boundary_rejected", "boundary": {"status": verdict.status.value, "detail": verdict.detail}}
    except LaneDispatchError as exc:
        return 502, {"error": str(exc)}
    except KeyError as exc:
        return 404, {"error": f"approval event not found: {exc.args[0]}"}
    except ValueError as exc:
        message = str(exc)
        if "already exists" in message or "already approved" in message or "already rejected" in message:
            return 409, {"error": message}
        return 400, {"error": message}


def _resolve_actor(*, config: ApiConfig, path: str, query: dict[str, list[str]], body: dict[str, Any], headers: dict[str, str]) -> Actor:
    if not path.startswith("/api/v1/"):
        return Actor.from_roles([])

    if path == "/api/v1/signup":
        return Actor.from_roles([])

    if config.authenticator is not None:
        try:
            return config.authenticator.authenticate(headers)
        except ApiAuthError as exc:
            api_key = (headers.get("x-api-key") or "").strip()
            if api_key and config.store_path is not None:
                store = _require_store(config)
                roles = store.roles_for_api_key(api_key)
                if roles:
                    return Actor.from_roles(roles)
            raise exc

    if isinstance(body.get("roles"), list):
        return _actor_from_sources(query_roles=body.get("roles", []), header_roles=headers.get("x-actor-roles", ""))
    return _actor_from_sources(query_roles=query.get("role", []), header_roles=headers.get("x-actor-roles", ""))


def _actor_from_sources(*, query_roles: Any, header_roles: str) -> Actor:
    roles: list[str] = []
    if isinstance(query_roles, list):
        roles.extend(str(item) for item in query_roles)
    if header_roles:
        roles.extend(part.strip() for part in header_roles.split(",") if part.strip())
    return Actor.from_roles(roles)


def _run_payload(record) -> dict[str, Any]:
    return {
        "run_id": record.run_id,
        "profile": record.profile,
        "mode": record.mode.value,
        "receipt_id": record.receipt_id,
        "boundary": {"status": record.boundary.status.value, "detail": record.boundary.detail},
        "sink": record.sink_result.sink,
        "artifact": None if record.sink_result.artifact is None else {"path": record.sink_result.artifact.path},
        "approval": None
        if record.sink_result.approval is None
        else {
            "event_id": record.sink_result.approval.event_id,
            "inbox": record.sink_result.approval.inbox,
            "approval_status": record.sink_result.approval.approval_status,
        },
        "preview_excerpt": record.sink_result.preview_excerpt,
    }


def _issued_key_view(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "api_key": row["api_key"],
        "signup_request_id": row["signup_request_id"],
        "email": row["email"],
        "signup_status": row.get("signup_status"),
        "roles": list(row.get("roles", ())),
        "is_active": bool(row.get("is_active")),
        "created_at": row.get("created_at"),
    }


def _profile_meta_view(meta: profiles_registry.ProfileMeta) -> dict[str, Any]:
    return {
        "name": meta.name,
        "summary": meta.summary,
        "necessary": meta.necessary,
        "sink": meta.sink,
        "content_types": list(meta.content_types),
        "safety": dict(meta.safety),
    }


def _signup_view(row: dict[str, Any]) -> dict[str, Any]:
    data = {
        "id": row["id"],
        "email": row["email"],
        "requested_roles": list(row.get("requested_roles", ())),
        "status": row["status"],
        "approved_roles": list(row.get("approved_roles", ())),
        "note": row.get("note"),
        "decided_by": row.get("decided_by"),
        "decided_at": row.get("decided_at"),
        "created_at": row.get("created_at"),
    }
    if "api_key" in row:
        data["api_key"] = row["api_key"]
    return data


def _approval_view(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": row["event_id"],
        "run_id": row["run_id"],
        "inbox": row["inbox"],
        "approval_status": row["approval_status"],
        "payload": row.get("payload"),
        "decided_by": row.get("decided_by"),
        "note": row.get("note"),
        "decided_at": row.get("decided_at"),
    }


def _headers(environ: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in environ.items():
        if not key.startswith("HTTP_"):
            continue
        name = key[5:].lower().replace("_", "-")
        result[name] = str(value)
    return result


def _read_json_body(environ: dict[str, Any]) -> dict[str, Any]:
    if environ.get("REQUEST_METHOD", "GET").upper() not in {"POST", "PUT", "PATCH"}:
        return {}
    length_text = str(environ.get("CONTENT_LENGTH") or "0")
    try:
        length = int(length_text)
    except ValueError:
        length = 0
    if length <= 0:
        return {}
    raw = environ["wsgi.input"].read(length)
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def _require_store(config: ApiConfig) -> RunStore:
    if config.store_path is None:
        raise ValueError("store_path is required for this endpoint")
    store = RunStore(config.store_path)
    store.init_schema()
    return store


def _reason_phrase(status: int) -> str:
    phrases = {200: "OK", 201: "Created", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 409: "Conflict", 422: "Unprocessable Entity", 502: "Bad Gateway"}
    return phrases.get(status, "OK")


def _cors_headers() -> list[tuple[str, str]]:
    return [
        ("Access-Control-Allow-Origin", "*"),
        ("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,OPTIONS"),
        ("Access-Control-Allow-Headers", "Content-Type,x-api-key,x-actor-roles"),
    ]
