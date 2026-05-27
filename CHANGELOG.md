# Changelog

All notable soRai rebuild checkpoints are tracked here.

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
