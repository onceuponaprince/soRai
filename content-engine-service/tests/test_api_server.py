from __future__ import annotations

from pathlib import Path

from content_engine_service.access_policy import AccessPolicy
from content_engine_service.api_server import ApiConfig, handle_request


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
