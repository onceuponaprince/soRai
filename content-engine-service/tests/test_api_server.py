from __future__ import annotations

from io import BytesIO
from pathlib import Path

from content_engine_service.access_policy import AccessPolicy
from content_engine_service.api_server import ApiConfig, create_wsgi_app, handle_request


ENGINE_ROOT = Path(__file__).resolve().parents[2] / "content-engine"


def _config(tmp_path, *, mock_output="mock response"):
    return ApiConfig(
        engine_root=ENGINE_ROOT,
        artifact_root=tmp_path / "artifacts",
        policy=AccessPolicy.default(),
        store_path=tmp_path / "runs.sqlite3",
        mock_output=mock_output,
    )


def test_health_endpoint(tmp_path):
    status, payload = handle_request(config=_config(tmp_path), method="GET", path="/health", query={}, body={}, headers={})
    assert status == 200
    assert payload == {"status": "ok"}


def test_profiles_endpoint_filters_by_role(tmp_path):
    status, payload = handle_request(config=_config(tmp_path), method="GET", path="/api/v1/profiles", query={"role": ["approver"]}, body={}, headers={})
    assert status == 200
    assert payload["profiles"] == ["build-in-public", "general"]


def test_runs_endpoint_creates_record_and_artifact(tmp_path):
    cfg = _config(tmp_path, mock_output="artifact output")
    status, payload = handle_request(
        config=cfg,
        method="POST",
        path="/api/v1/runs",
        query={},
        body={"profile": "general", "brief": "Write a note", "roles": ["operator"], "mode": "stage"},
        headers={},
    )
    assert status == 201
    assert payload["artifact"]["path"]

    status2, runs_payload = handle_request(config=cfg, method="GET", path="/api/v1/runs", query={}, body={}, headers={})
    assert status2 == 200
    assert len(runs_payload["runs"]) == 1
    assert runs_payload["runs"][0]["profile"] == "general"


def test_runs_endpoint_enforces_access_policy(tmp_path):
    cfg = _config(tmp_path)
    status, payload = handle_request(
        config=cfg,
        method="POST",
        path="/api/v1/runs",
        query={},
        body={"profile": "build-in-public", "brief": "Write a note", "roles": ["operator"], "mode": "stage"},
        headers={},
    )
    assert status == 403
    assert "not allowed" in payload["error"]


def test_approvals_endpoint_returns_inbox_events(tmp_path):
    cfg = _config(tmp_path, mock_output="approval output")
    status, payload = handle_request(
        config=cfg,
        method="POST",
        path="/api/v1/runs",
        query={},
        body={"profile": "build-in-public", "brief": "Write a note", "roles": ["approver"], "mode": "stage"},
        headers={},
    )
    assert status == 201
    assert payload["approval"]["inbox"] == "borai-inbox"

    status2, approvals_payload = handle_request(config=cfg, method="GET", path="/api/v1/approvals", query={}, body={}, headers={})
    assert status2 == 200
    assert len(approvals_payload["approvals"]) == 1
    assert approvals_payload["approvals"][0]["inbox"] == "borai-inbox"



def _create_pending_approval(cfg):
    status, payload = handle_request(
        config=cfg,
        method="POST",
        path="/api/v1/runs",
        query={},
        body={"profile": "build-in-public", "brief": "Write a note", "roles": ["approver"], "mode": "stage"},
        headers={},
    )
    assert status == 201
    assert payload["approval"] is not None
    return payload["approval"]["event_id"]


def test_approval_decision_approve_endpoint(tmp_path):
    cfg = _config(tmp_path, mock_output="approval output")
    event_id = _create_pending_approval(cfg)

    status, payload = handle_request(
        config=cfg,
        method="POST",
        path=f"/api/v1/approvals/{event_id}/approve",
        query={},
        body={"roles": ["approver"], "note": "looks good"},
        headers={},
    )
    assert status == 200
    assert payload["approval"]["approval_status"] == "approved"
    assert payload["approval"]["note"] == "looks good"
    assert payload["approval"]["decided_by"] == "approver"


def test_approval_decision_reject_endpoint(tmp_path):
    cfg = _config(tmp_path, mock_output="approval output")
    event_id = _create_pending_approval(cfg)

    status, payload = handle_request(
        config=cfg,
        method="POST",
        path=f"/api/v1/approvals/{event_id}/reject",
        query={},
        body={"roles": ["admin"], "note": "needs revision"},
        headers={},
    )
    assert status == 200
    assert payload["approval"]["approval_status"] == "rejected"
    assert payload["approval"]["note"] == "needs revision"
    assert payload["approval"]["decided_by"] == "admin"


def test_approval_decision_requires_approver_or_admin(tmp_path):
    cfg = _config(tmp_path, mock_output="approval output")
    event_id = _create_pending_approval(cfg)

    status, payload = handle_request(
        config=cfg,
        method="POST",
        path=f"/api/v1/approvals/{event_id}/approve",
        query={},
        body={"roles": ["operator"]},
        headers={},
    )
    assert status == 403
    assert "requires approver or admin" in payload["error"]


def test_approval_decision_cannot_decide_twice(tmp_path):
    cfg = _config(tmp_path, mock_output="approval output")
    event_id = _create_pending_approval(cfg)

    status, _ = handle_request(
        config=cfg,
        method="POST",
        path=f"/api/v1/approvals/{event_id}/approve",
        query={},
        body={"roles": ["approver"]},
        headers={},
    )
    assert status == 200

    status2, payload2 = handle_request(
        config=cfg,
        method="POST",
        path=f"/api/v1/approvals/{event_id}/reject",
        query={},
        body={"roles": ["approver"]},
        headers={},
    )
    assert status2 == 409
    assert "already approved" in payload2["error"]



def test_api_key_auth_enforces_header(tmp_path):
    from content_engine_service.api_auth import ApiKeyAuthenticator

    cfg = _config(tmp_path)
    cfg = ApiConfig(
        engine_root=cfg.engine_root,
        artifact_root=cfg.artifact_root,
        policy=cfg.policy,
        store_path=cfg.store_path,
        mock_output=cfg.mock_output,
        authenticator=ApiKeyAuthenticator(key_roles={"test-key": ("approver",)}),
    )

    status, payload = handle_request(config=cfg, method="GET", path="/api/v1/profiles", query={}, body={}, headers={})
    assert status == 401
    assert "x-api-key" in payload["error"]


def test_api_key_auth_uses_roles_from_key(tmp_path):
    from content_engine_service.api_auth import ApiKeyAuthenticator

    cfg = _config(tmp_path, mock_output="approval output")
    cfg = ApiConfig(
        engine_root=cfg.engine_root,
        artifact_root=cfg.artifact_root,
        policy=cfg.policy,
        store_path=cfg.store_path,
        mock_output=cfg.mock_output,
        authenticator=ApiKeyAuthenticator(key_roles={"approver-key": ("approver",)}),
    )

    status, payload = handle_request(
        config=cfg,
        method="POST",
        path="/api/v1/runs",
        query={},
        body={"profile": "build-in-public", "brief": "Write a note", "mode": "stage", "roles": ["operator"]},
        headers={"x-api-key": "approver-key"},
    )
    assert status == 201
    assert payload["approval"]["inbox"] == "borai-inbox"



def test_signup_request_and_admin_approval_lifecycle(tmp_path):
    cfg = _config(tmp_path, mock_output="ignored")

    status, payload = handle_request(
        config=cfg,
        method="POST",
        path="/api/v1/signup",
        query={},
        body={"email": "newuser@example.com", "requested_roles": ["operator"]},
        headers={},
    )
    assert status == 201
    signup_id = payload["signup"]["id"]
    assert payload["signup"]["status"] == "pending"

    status2, payload2 = handle_request(
        config=cfg,
        method="GET",
        path="/api/v1/signup/pending",
        query={},
        body={"roles": ["admin"]},
        headers={},
    )
    assert status2 == 200
    assert len(payload2["pending"]) == 1

    status3, payload3 = handle_request(
        config=cfg,
        method="POST",
        path=f"/api/v1/signup/{signup_id}/approve",
        query={},
        body={"roles": ["admin"], "approved_roles": ["operator"], "note": "approved"},
        headers={},
    )
    assert status3 == 200
    assert payload3["signup"]["status"] == "approved"
    issued_key = payload3["api_key"]
    assert issued_key.startswith("sorai_")

    status4, payload4 = handle_request(
        config=cfg,
        method="POST",
        path="/api/v1/runs",
        query={},
        body={"profile": "general", "brief": "Write with key", "mode": "dry-run"},
        headers={"x-api-key": issued_key},
    )
    assert status4 == 201
    assert payload4["profile"] == "general"


def test_signup_pending_requires_admin(tmp_path):
    cfg = _config(tmp_path)
    status, payload = handle_request(
        config=cfg,
        method="GET",
        path="/api/v1/signup/pending",
        query={},
        body={"roles": ["operator"]},
        headers={},
    )
    assert status == 403
    assert "admin role" in payload["error"]


def test_signup_duplicate_request_conflicts(tmp_path):
    cfg = _config(tmp_path)
    first_status, _ = handle_request(
        config=cfg,
        method="POST",
        path="/api/v1/signup",
        query={},
        body={"email": "dup@example.com"},
        headers={},
    )
    assert first_status == 201

    second_status, payload = handle_request(
        config=cfg,
        method="POST",
        path="/api/v1/signup",
        query={},
        body={"email": "dup@example.com"},
        headers={},
    )
    assert second_status == 409
    assert "already exists" in payload["error"]



def test_whoami_endpoint(tmp_path):
    cfg = _config(tmp_path)
    status, payload = handle_request(
        config=cfg,
        method="GET",
        path="/api/v1/whoami",
        query={"role": ["approver"]},
        body={},
        headers={},
    )
    assert status == 200
    assert payload["roles"] == ["approver"]


def test_admin_api_key_inventory_and_revoke_reactivate(tmp_path):
    from content_engine_service.api_auth import ApiKeyAuthenticator

    cfg = _config(tmp_path, mock_output="ignored")
    cfg = ApiConfig(
        engine_root=cfg.engine_root,
        artifact_root=cfg.artifact_root,
        policy=cfg.policy,
        store_path=cfg.store_path,
        mock_output=cfg.mock_output,
        authenticator=ApiKeyAuthenticator(key_roles={"admin-key": ("admin",)}),
    )

    status_signup, payload_signup = handle_request(
        config=cfg,
        method="POST",
        path="/api/v1/signup",
        query={},
        body={"email": "ops@example.com", "requested_roles": ["operator"]},
        headers={},
    )
    assert status_signup == 201
    signup_id = payload_signup["signup"]["id"]

    status_approve, payload_approve = handle_request(
        config=cfg,
        method="POST",
        path=f"/api/v1/signup/{signup_id}/approve",
        query={},
        body={"roles": ["admin"], "approved_roles": ["operator"]},
        headers={"x-api-key": "admin-key"},
    )
    assert status_approve == 200
    issued_key = payload_approve["api_key"]

    status_keys, payload_keys = handle_request(
        config=cfg,
        method="GET",
        path="/api/v1/admin/api-keys",
        query={},
        body={"roles": ["admin"]},
        headers={"x-api-key": "admin-key"},
    )
    assert status_keys == 200
    assert len(payload_keys["api_keys"]) == 1
    assert payload_keys["api_keys"][0]["api_key"] == issued_key
    assert payload_keys["api_keys"][0]["is_active"] is True

    status_revoke, payload_revoke = handle_request(
        config=cfg,
        method="POST",
        path=f"/api/v1/admin/api-keys/{issued_key}/revoke",
        query={},
        body={"roles": ["admin"]},
        headers={"x-api-key": "admin-key"},
    )
    assert status_revoke == 200
    assert payload_revoke["api_key"]["is_active"] is False

    status_run_blocked, payload_run_blocked = handle_request(
        config=cfg,
        method="POST",
        path="/api/v1/runs",
        query={},
        body={"profile": "general", "brief": "test", "mode": "dry-run"},
        headers={"x-api-key": issued_key},
    )
    assert status_run_blocked == 401

    status_reactivate, payload_reactivate = handle_request(
        config=cfg,
        method="POST",
        path=f"/api/v1/admin/api-keys/{issued_key}/reactivate",
        query={},
        body={"roles": ["admin"]},
        headers={"x-api-key": "admin-key"},
    )
    assert status_reactivate == 200
    assert payload_reactivate["api_key"]["is_active"] is True

    status_run_ok, payload_run_ok = handle_request(
        config=cfg,
        method="POST",
        path="/api/v1/runs",
        query={},
        body={"profile": "general", "brief": "test", "mode": "dry-run"},
        headers={"x-api-key": issued_key},
    )
    assert status_run_ok == 201
    assert payload_run_ok["profile"] == "general"


def test_admin_api_key_inventory_requires_admin(tmp_path):
    cfg = _config(tmp_path)
    status, payload = handle_request(
        config=cfg,
        method="GET",
        path="/api/v1/admin/api-keys",
        query={},
        body={"roles": ["operator"]},
        headers={},
    )
    assert status == 403
    assert "admin role required" in payload["error"]


def _call_wsgi(app, *, method: str, path: str) -> tuple[str, dict[str, str], bytes]:
    status_line = ""
    response_headers: dict[str, str] = {}

    def _start_response(status, headers):
        nonlocal status_line
        status_line = status
        response_headers.update({k: v for k, v in headers})

    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "CONTENT_LENGTH": "0",
        "wsgi.input": BytesIO(b""),
    }
    body = b"".join(app(environ, _start_response))
    return status_line, response_headers, body


def test_wsgi_app_includes_cors_headers(tmp_path):
    app = create_wsgi_app(_config(tmp_path))
    status, headers, _ = _call_wsgi(app, method="GET", path="/health")
    assert status.startswith("200")
    assert headers["Access-Control-Allow-Origin"] == "*"
    assert "OPTIONS" in headers["Access-Control-Allow-Methods"]
    assert "x-api-key" in headers["Access-Control-Allow-Headers"]


def test_wsgi_app_handles_options_preflight(tmp_path):
    app = create_wsgi_app(_config(tmp_path))
    status, headers, body = _call_wsgi(app, method="OPTIONS", path="/api/v1/runs")
    assert status.startswith("204")
    assert headers["Content-Length"] == "0"
    assert headers["Access-Control-Allow-Origin"] == "*"
    assert body == b""
