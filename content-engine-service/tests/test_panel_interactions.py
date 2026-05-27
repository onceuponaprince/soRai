from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

playwright_sync = pytest.importorskip("playwright.sync_api")
sync_playwright = playwright_sync.sync_playwright


PANEL_ROOT = Path(__file__).resolve().parents[1] / "panel"


class _PanelHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PANEL_ROOT), **kwargs)

    def log_message(self, format, *args):  # noqa: A003
        return


def _start_server(handler_cls) -> tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    return server, base_url


def _stop_server(server: ThreadingHTTPServer) -> None:
    server.shutdown()
    server.server_close()


def _mock_api_handler_factory():
    state: dict[str, Any] = {
        "next_signup_id": 2,
        "pending": [
            {
                "id": 1,
                "email": "pending@example.com",
                "requested_roles": ["operator"],
                "status": "pending",
            }
        ],
        "approvals": [
            {
                "event_id": "evt-1",
                "run_id": "run-1",
                "inbox": "borai-inbox",
                "approval_status": "pending",
            }
        ],
        "api_keys": [
            {
                "api_key": "issued-1",
                "signup_request_id": 1,
                "email": "pending@example.com",
                "roles": ["operator"],
                "is_active": True,
                "created_at": "2026-05-27T00:00:00Z",
            }
        ],
    }

    class _MockApiHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):  # noqa: A003
            return

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type,x-api-key,x-actor-roles")
            self.end_headers()
            self.wfile.write(raw)

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length <= 0:
                return {}
            raw = self.rfile.read(length)
            if not raw:
                return {}
            return json.loads(raw.decode("utf-8"))

        def do_OPTIONS(self):  # noqa: N802
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type,x-api-key,x-actor-roles")
            self.end_headers()

        def do_GET(self):  # noqa: N802
            if self.path == "/health":
                return self._send_json(200, {"status": "ok"})
            if self.path == "/api/v1/whoami":
                return self._send_json(200, {"roles": ["admin"]})
            if self.path == "/api/v1/profiles":
                return self._send_json(200, {"profiles": ["general", "build-in-public"], "roles": ["admin"]})
            if self.path == "/api/v1/signup/pending":
                return self._send_json(200, {"pending": state["pending"]})
            if self.path == "/api/v1/approvals":
                return self._send_json(200, {"approvals": state["approvals"]})
            if self.path == "/api/v1/admin/api-keys":
                return self._send_json(200, {"api_keys": state["api_keys"]})
            return self._send_json(404, {"error": "not found"})

        def do_POST(self):  # noqa: N802
            body = self._read_json()

            if self.path == "/api/v1/signup":
                signup_id = int(state["next_signup_id"])
                state["next_signup_id"] = signup_id + 1
                signup = {
                    "id": signup_id,
                    "email": str(body.get("email", "new@example.com")),
                    "requested_roles": body.get("requested_roles", ["operator"]),
                    "status": "pending",
                }
                state["pending"].append(signup)
                return self._send_json(201, {"signup": signup})

            if self.path.startswith("/api/v1/signup/") and self.path.endswith("/approve"):
                signup_id = int(self.path.split("/")[4])
                state["pending"] = [item for item in state["pending"] if item["id"] != signup_id]
                return self._send_json(200, {"signup": {"id": signup_id, "status": "approved"}})

            if self.path.startswith("/api/v1/signup/") and self.path.endswith("/reject"):
                signup_id = int(self.path.split("/")[4])
                state["pending"] = [item for item in state["pending"] if item["id"] != signup_id]
                return self._send_json(200, {"signup": {"id": signup_id, "status": "rejected"}})

            if self.path == "/api/v1/runs":
                return self._send_json(
                    201,
                    {
                        "run_id": "run-new",
                        "profile": body.get("profile", "general"),
                        "mode": body.get("mode", "dry-run"),
                        "artifact": {"path": "/tmp/sorai-artifacts/run-new.txt"},
                        "approval": None,
                    },
                )

            if self.path.startswith("/api/v1/approvals/") and self.path.endswith("/approve"):
                event_id = self.path.split("/")[4]
                for row in state["approvals"]:
                    if row["event_id"] == event_id:
                        row["approval_status"] = "approved"
                return self._send_json(200, {"ok": True})

            if self.path.startswith("/api/v1/approvals/") and self.path.endswith("/reject"):
                event_id = self.path.split("/")[4]
                for row in state["approvals"]:
                    if row["event_id"] == event_id:
                        row["approval_status"] = "rejected"
                return self._send_json(200, {"ok": True})

            if self.path.startswith("/api/v1/admin/api-keys/") and self.path.endswith("/revoke"):
                api_key = self.path.split("/")[5]
                for row in state["api_keys"]:
                    if row["api_key"] == api_key:
                        row["is_active"] = False
                return self._send_json(200, {"ok": True})

            if self.path.startswith("/api/v1/admin/api-keys/") and self.path.endswith("/reactivate"):
                api_key = self.path.split("/")[5]
                for row in state["api_keys"]:
                    if row["api_key"] == api_key:
                        row["is_active"] = True
                return self._send_json(200, {"ok": True})

            return self._send_json(404, {"error": "not found"})

    return _MockApiHandler


@pytest.fixture()
def panel_and_api_urls():
    panel_server, panel_url = _start_server(_PanelHandler)
    api_handler = _mock_api_handler_factory()
    api_server, api_url = _start_server(api_handler)
    try:
        yield panel_url, api_url
    finally:
        _stop_server(panel_server)
        _stop_server(api_server)


@pytest.fixture()
def browser_page():
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover - environment dependent
            pytest.skip(f"playwright chromium unavailable: {exc}")
        page = browser.new_page()
        try:
            yield page
        finally:
            page.close()
            browser.close()


def _wait_text(page, selector: str, needle: str) -> None:
    page.wait_for_function(
        "([selector, needle]) => document.querySelector(selector).textContent.includes(needle)",
        arg=[selector, needle],
        timeout=5000,
    )


def test_panel_clicks_render_core_responses(browser_page, panel_and_api_urls):
    panel_url, api_url = panel_and_api_urls
    page = browser_page
    page.goto(panel_url, wait_until="domcontentloaded")
    page.fill("#apiBase", api_url)
    page.fill("#apiKey", "admin-key")

    page.click("#healthBtn")
    _wait_text(page, "#healthOut", '"status": 200')

    page.click("#whoamiBtn")
    _wait_text(page, "#whoamiOut", '"admin"')

    page.click("#profilesBtn")
    _wait_text(page, "#profilesOut", '"general"')


def test_panel_forms_and_admin_actions(browser_page, panel_and_api_urls):
    panel_url, api_url = panel_and_api_urls
    page = browser_page
    page.goto(panel_url, wait_until="domcontentloaded")
    page.fill("#apiBase", api_url)
    page.fill("#apiKey", "admin-key")

    page.fill("#signupForm input[name='email']", "newuser@example.com")
    page.click("#signupForm button[type='submit']")
    _wait_text(page, "#signupOut", '"status": 201')

    page.click("#pendingBtn")
    page.wait_for_selector("#pendingList .row")
    page.click("#pendingList button[data-action='approve']")
    page.wait_for_timeout(100)

    page.fill("#runForm textarea[name='brief']", "panel run")
    page.click("#runForm button[type='submit']")
    _wait_text(page, "#runOut", '"status": 201')

    page.click("#approvalsBtn")
    page.wait_for_selector("#approvalsList .row")
    page.click("#approvalsList button[data-action='approve']")
    page.wait_for_timeout(100)

    page.click("#keysBtn")
    page.wait_for_selector("#keysList .row")
    page.click("#keysList button[data-action='revoke']")
    page.wait_for_timeout(100)
    page.click("#keysList button[data-action='reactivate']")
