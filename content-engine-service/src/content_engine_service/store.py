from __future__ import annotations

import json
import secrets
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from content_engine_service.run_types import BoundaryVerdict, RunMode, SinkResult


@dataclass(frozen=True)
class StoredRun:
    id: str
    profile: str
    mode: str
    receipt_id: str | None
    boundary_status: str
    boundary_detail: str
    sink: str


class RunStore:
    """Small SQLite store for service-library runs and sink records."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def init_schema(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                create table if not exists runs (
                  id text primary key,
                  profile text not null,
                  mode text not null,
                  receipt_id text,
                  boundary_status text not null,
                  boundary_detail text not null,
                  sink text not null,
                  created_at text not null default current_timestamp
                );

                create table if not exists artifacts (
                  id integer primary key autoincrement,
                  run_id text not null references runs(id),
                  path text not null,
                  content_type text not null,
                  created_at text not null default current_timestamp
                );

                create table if not exists approval_events (
                  event_id text primary key,
                  run_id text not null references runs(id),
                  inbox text not null,
                  approval_status text not null,
                  payload_json text not null,
                  decided_by text,
                  note text,
                  decided_at text,
                  created_at text not null default current_timestamp
                );

                create table if not exists signup_requests (
                  id integer primary key autoincrement,
                  email text not null unique,
                  requested_roles_json text not null,
                  status text not null,
                  approved_roles_json text,
                  note text,
                  decided_by text,
                  decided_at text,
                  created_at text not null default current_timestamp
                );

                create table if not exists issued_api_keys (
                  api_key text primary key,
                  signup_request_id integer not null references signup_requests(id),
                  roles_json text not null,
                  is_active integer not null default 1,
                  created_at text not null default current_timestamp
                );
                """
            )
            self._ensure_column(conn, "approval_events", "decided_by", "text")
            self._ensure_column(conn, "approval_events", "note", "text")
            self._ensure_column(conn, "approval_events", "decided_at", "text")
            self._ensure_column(conn, "signup_requests", "approved_roles_json", "text")
            self._ensure_column(conn, "signup_requests", "note", "text")
            self._ensure_column(conn, "signup_requests", "decided_by", "text")
            self._ensure_column(conn, "signup_requests", "decided_at", "text")


    def record_run(
        self,
        *,
        run_id: str,
        profile: str,
        mode: RunMode,
        receipt_id: str | None,
        boundary: BoundaryVerdict,
        sink: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert into runs (id, profile, mode, receipt_id, boundary_status, boundary_detail, sink)
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, profile, mode.value, receipt_id, boundary.status.value, boundary.detail, sink),
            )

    def record_sink_result(self, *, run_id: str, profile: str, output: str, sink_result: SinkResult) -> None:
        with self._connect() as conn:
            if sink_result.artifact is not None:
                conn.execute(
                    "insert into artifacts (run_id, path, content_type) values (?, ?, ?)",
                    (run_id, sink_result.artifact.path, sink_result.artifact.content_type),
                )
            if sink_result.approval is not None:
                payload = {"profile": profile, "output": output}
                conn.execute(
                    """
                    insert into approval_events (event_id, run_id, inbox, approval_status, payload_json)
                    values (?, ?, ?, ?, ?)
                    """,
                    (
                        sink_result.approval.event_id,
                        run_id,
                        sink_result.approval.inbox,
                        sink_result.approval.approval_status,
                        json.dumps(payload, sort_keys=True),
                    ),
                )

    def get_run(self, run_id: str) -> StoredRun | None:
        with self._connect() as conn:
            row = conn.execute(
                "select id, profile, mode, receipt_id, boundary_status, boundary_detail, sink from runs where id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return StoredRun(**dict(row))

    def list_runs(self) -> list[StoredRun]:
        with self._connect() as conn:
            rows = conn.execute(
                "select id, profile, mode, receipt_id, boundary_status, boundary_detail, sink from runs order by created_at desc, id desc"
            ).fetchall()
        return [StoredRun(**dict(row)) for row in rows]

    def list_artifacts(self, run_id: str | None = None) -> list[dict[str, Any]]:
        return self._list_rows("artifacts", run_id)

    def list_approval_events(self, run_id: str | None = None) -> list[dict[str, Any]]:
        rows = self._list_rows("approval_events", run_id)
        for row in rows:
            row["payload"] = json.loads(row.pop("payload_json"))
        return rows

    def get_approval_event(self, event_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "select * from approval_events where event_id = ?",
                (event_id,),
            ).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["payload"] = json.loads(data.pop("payload_json"))
        return data

    def decide_approval(self, *, event_id: str, decision: str, decided_by: str, note: str = "") -> dict[str, Any]:
        if decision not in {"approved", "rejected"}:
            raise ValueError(f"invalid decision: {decision}")
        with self._connect() as conn:
            row = conn.execute(
                "select approval_status from approval_events where event_id = ?",
                (event_id,),
            ).fetchone()
            if row is None:
                raise KeyError(event_id)
            if row["approval_status"] != "pending":
                raise ValueError(f"approval event already {row['approval_status']}")
            conn.execute(
                """
                update approval_events
                set approval_status = ?, decided_by = ?, note = ?, decided_at = current_timestamp
                where event_id = ?
                """,
                (decision, decided_by, note, event_id),
            )
        updated = self.get_approval_event(event_id)
        assert updated is not None
        return updated

    def request_signup(self, *, email: str, requested_roles: tuple[str, ...] = ("operator",)) -> dict[str, Any]:
        normalized_email = email.strip().lower()
        if not normalized_email:
            raise ValueError("email is required")
        roles = tuple(sorted({role.strip().lower() for role in requested_roles if role.strip()}))
        if not roles:
            roles = ("operator",)

        with self._connect() as conn:
            existing = conn.execute("select id from signup_requests where email = ?", (normalized_email,)).fetchone()
            if existing is not None:
                raise ValueError("signup request already exists for this email")
            conn.execute(
                """
                insert into signup_requests (email, requested_roles_json, status)
                values (?, ?, 'pending')
                """,
                (normalized_email, json.dumps(list(roles), sort_keys=True)),
            )
            row = conn.execute("select * from signup_requests where email = ?", (normalized_email,)).fetchone()
        assert row is not None
        return self._signup_row(dict(row))

    def list_signup_requests(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if status is None:
                rows = conn.execute("select * from signup_requests order by created_at desc, id desc").fetchall()
            else:
                rows = conn.execute("select * from signup_requests where status = ? order by created_at desc, id desc", (status,)).fetchall()
        return [self._signup_row(dict(row)) for row in rows]

    def approve_signup(self, *, signup_id: int, approved_by: str, approved_roles: tuple[str, ...] | None = None, note: str = "") -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("select * from signup_requests where id = ?", (signup_id,)).fetchone()
            if row is None:
                raise KeyError(signup_id)
            current = dict(row)
            if current["status"] != "pending":
                raise ValueError(f"signup request already {current['status']}")

            roles = approved_roles or tuple(json.loads(current["requested_roles_json"]))
            normalized_roles = tuple(sorted({role.strip().lower() for role in roles if str(role).strip()}))
            if not normalized_roles:
                normalized_roles = ("operator",)

            conn.execute(
                """
                update signup_requests
                set status = 'approved', approved_roles_json = ?, note = ?, decided_by = ?, decided_at = current_timestamp
                where id = ?
                """,
                (json.dumps(list(normalized_roles), sort_keys=True), note, approved_by, signup_id),
            )

            api_key = self._generate_api_key(conn)
            conn.execute(
                """
                insert into issued_api_keys (api_key, signup_request_id, roles_json, is_active)
                values (?, ?, ?, 1)
                """,
                (api_key, signup_id, json.dumps(list(normalized_roles), sort_keys=True)),
            )

        record = self.get_signup_request(signup_id)
        assert record is not None
        record["api_key"] = api_key
        return record

    def reject_signup(self, *, signup_id: int, decided_by: str, note: str = "") -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("select * from signup_requests where id = ?", (signup_id,)).fetchone()
            if row is None:
                raise KeyError(signup_id)
            current = dict(row)
            if current["status"] != "pending":
                raise ValueError(f"signup request already {current['status']}")
            conn.execute(
                """
                update signup_requests
                set status = 'rejected', note = ?, decided_by = ?, decided_at = current_timestamp
                where id = ?
                """,
                (note, decided_by, signup_id),
            )
        record = self.get_signup_request(signup_id)
        assert record is not None
        return record

    def get_signup_request(self, signup_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("select * from signup_requests where id = ?", (signup_id,)).fetchone()
        if row is None:
            return None
        return self._signup_row(dict(row))

    def roles_for_api_key(self, api_key: str) -> tuple[str, ...] | None:
        key = api_key.strip()
        if not key:
            return None
        with self._connect() as conn:
            row = conn.execute(
                "select roles_json from issued_api_keys where api_key = ? and is_active = 1",
                (key,),
            ).fetchone()
        if row is None:
            return None
        roles = json.loads(row["roles_json"])
        return tuple(sorted(str(role).strip().lower() for role in roles if str(role).strip()))

    def _signup_row(self, row: dict[str, Any]) -> dict[str, Any]:
        row["requested_roles"] = tuple(json.loads(row.pop("requested_roles_json")))
        approved_json = row.pop("approved_roles_json")
        row["approved_roles"] = tuple(json.loads(approved_json)) if approved_json else ()
        return row

    def _generate_api_key(self, conn: sqlite3.Connection) -> str:
        for _ in range(20):
            candidate = "sorai_" + secrets.token_urlsafe(24)
            exists = conn.execute("select 1 from issued_api_keys where api_key = ?", (candidate,)).fetchone()
            if exists is None:
                return candidate
        raise RuntimeError("failed to generate unique api key")

    def _list_rows(self, table: str, run_id: str | None) -> list[dict[str, Any]]:
        if table not in {"artifacts", "approval_events"}:
            raise ValueError(f"unsupported table: {table}")
        with self._connect() as conn:
            if run_id is None:
                rows = conn.execute(f"select * from {table} order by created_at desc").fetchall()
            else:
                rows = conn.execute(f"select * from {table} where run_id = ? order by created_at asc", (run_id,)).fetchall()
        return [dict(row) for row in rows]

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
        columns = {row[1] for row in conn.execute(f"pragma table_info({table})")}
        if column not in columns:
            conn.execute(f"alter table {table} add column {column} {column_type}")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("pragma foreign_keys = on")
        return conn
