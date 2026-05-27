# Changelog

All notable soRai rebuild checkpoints are tracked here.

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
