# Changelog

All notable soRai rebuild checkpoints are tracked here.

## 0.14.0 - 2026-05-27

- Added `necessary` frontmatter status generation in `content-engine/lib/render.sh` and explicit necessity flags in profile TOMLs.
- Added profile-metadata API endpoint `GET /api/v1/profiles/meta` returning profile `summary`, `necessary`, `sink`, `content_types`, and `safety`.
- Added panel "Profile Metadata" view to inspect skill summary and necessity status from the API.
- Added test coverage for frontmatter necessity parsing, profile metadata propagation, API metadata endpoint behavior, and panel metadata interaction.

## 0.13.0 - 2026-05-27

- Added CORS and `OPTIONS` preflight support to the local WSGI API so the panel can call API endpoints from a different local port.
- Hardened panel request handling to surface network/CORS failures in UI output instead of failing silently.
- Added API CORS tests and Playwright-driven panel interaction tests that click core operator/admin controls end-to-end against mock API responses.

## 0.12.0 - 2026-05-27

- Added browser panel scaffold (`content-engine-service/panel/`) for direct operator/admin flow testing against local API endpoints.
- Added panel runtime docs and static serve instructions for local mock-data validation.
- Added front-facing scaffold contract tests for panel controls, route wiring, and local run instructions.

## 0.11.0 - 2026-05-27

- Added Django backend scaffold (`backend/`) with manage.py, settings, URLs, and WSGI/ASGI entrypoints.
- Added Django proxy view that routes `/api/v1/*` requests into the shared core API handler for parity.
- Added backend README with run instructions and environment expectations.
- Added optional Django bridge tests (health/profile parity, run when Django is installed).
- Added Django and pytest-django optional dependencies in `pyproject.toml`.

## 0.10.0 - 2026-05-27

- Added `GET /api/v1/whoami` for role introspection on current actor context.
- Added admin API-key inventory endpoint: `GET /api/v1/admin/api-keys`.
- Added admin key state endpoints: `POST /api/v1/admin/api-keys/<key>/revoke` and `/reactivate`.
- Extended store with issued-key listing/detail helpers and active-state toggling.
- Added tests for whoami, admin key management, and revoke/reactivate auth effects.

## 0.9.0 - 2026-05-27

- Added pending-user signup flow with admin approval/rejection endpoints.
- Added persisted signup requests and lifecycle states (`pending`, `approved`, `rejected`).
- Added API-key issuance on signup approval and store-backed API-key role lookup.
- Added API auth fallback to store-issued keys when static key map auth is enabled.
- Added end-to-end tests for signup requests, admin approvals, conflict handling, and issued-key access.

## 0.8.0 - 2026-05-27

- Added optional API-key authentication for HTTP endpoints under `/api/v1/*`.
- Added `x-api-key` role binding via JSON key map (`{api_key: [roles...]}`).
- Added CLI `serve --api-keys <file.json>` support for enabling API-key auth.
- Enforced authenticated role derivation when API-key auth is enabled, ignoring request-body role overrides.
- Added auth unit tests and API integration tests for missing/invalid keys and role derivation.

## 0.7.0 - 2026-05-27

- Added approval decision endpoints: `POST /api/v1/approvals/<event_id>/approve` and `/reject`.
- Added decision metadata persistence (`decided_by`, `note`, `decided_at`) in SQLite approval events.
- Added schema-upgrade guards for older SQLite files missing new decision columns.
- Added approval lifecycle API tests for approve/reject, role checks, and repeat-decision protection.

## 0.6.0 - 2026-05-27

- Added minimal HTTP API layer with `/health`, `/api/v1/profiles`, `/api/v1/runs`, and `/api/v1/approvals`.
- Added CLI `serve` command to run the local WSGI API service.
- Added store read helpers to list artifacts and approval events globally or per run.
- Added API tests covering role-filtered profiles, staged runs, access denial, and approval listing.

## 0.5.0 - 2026-05-27

- Added role-aware profile access policy for public, operator, approver, and admin scopes.
- Added JSON allowlist loading for custom profile access rules.
- Added CLI profile filtering and render/run access checks.
- Added RBAC tests for default policy, custom allowlists, denial, and staged approval access.

## 0.4.0 - 2026-05-27

- Added service lane adapter and CLI commands.
- Added SQLite-backed run, artifact, and approval-event persistence.
- Added service core pipeline: profile rendering, frontmatter parsing, boundary validation, and sink routing.
- Added standalone content-engine renderer with generated `frontmatter.yaml`.
- Initialized the soRai rebuild workspace.

Commits:

- `ba3049c` feat: add service lane adapter and cli
- `ce47cc8` feat: add service core pipeline and persistence
- `b72dfc3` feat: add content-engine renderer checkpoint
- `d55ecf5` chore: initialize soRai rebuild workspace
