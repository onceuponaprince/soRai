from __future__ import annotations

import json
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
                  created_at text not null default current_timestamp
                );
                """
            )

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

    def _list_rows(self, table: str, run_id: str | None) -> list[dict[str, Any]]:
        if table not in {"artifacts", "approval_events"}:
            raise ValueError(f"unsupported table: {table}")
        with self._connect() as conn:
            if run_id is None:
                rows = conn.execute(f"select * from {table} order by created_at desc").fetchall()
            else:
                rows = conn.execute(f"select * from {table} where run_id = ? order by created_at asc", (run_id,)).fetchall()
        return [dict(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("pragma foreign_keys = on")
        return conn
