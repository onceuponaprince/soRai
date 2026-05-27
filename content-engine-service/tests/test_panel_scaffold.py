from __future__ import annotations

from pathlib import Path


PANEL_ROOT = Path(__file__).resolve().parents[1] / "panel"


def _read(path: str) -> str:
    return (PANEL_ROOT / path).read_text(encoding="utf-8")


def test_panel_index_has_expected_controls():
    index_html = _read("index.html")
    expected_ids = [
        "apiBase",
        "apiKey",
        "healthBtn",
        "whoamiBtn",
        "profilesBtn",
        "profileMetaBtn",
        "signupForm",
        "pendingBtn",
        "runForm",
        "approvalsBtn",
        "keysBtn",
    ]
    for control_id in expected_ids:
        assert f'id="{control_id}"' in index_html


def test_panel_js_wires_expected_api_routes():
    app_js = _read("app.js")
    expected_routes = [
        "/health",
        "/api/v1/whoami",
        "/api/v1/profiles",
        "/api/v1/profiles/meta",
        "/api/v1/signup",
        "/api/v1/signup/pending",
        "/api/v1/runs",
        "/api/v1/approvals",
        "/api/v1/admin/api-keys",
    ]
    for route in expected_routes:
        assert route in app_js


def test_panel_readme_includes_local_serve_flow():
    readme = _read("README.md")
    assert "python3 -m http.server 8787" in readme
    assert "http://127.0.0.1:8787" in readme
