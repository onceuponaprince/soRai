from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from content_engine_service.run_types import ApprovalRef, ArtifactRef, RunMode, SinkResult

INBOX_SINKS = frozenset({"borai-inbox", "borai-content-inbox"})


def route(*, sink: str, output: str, profile: str, mode: RunMode, run_id: str, artifact_root: Path) -> SinkResult:
    if mode is RunMode.DRY_RUN:
        return SinkResult(sink=sink, preview_excerpt=output[:200])

    if sink == "workspace-files":
        rel_path = f"{_slug(profile)}/{run_id}.md"
        path = Path(artifact_root) / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output)
        return SinkResult(sink=sink, artifact=ArtifactRef(path=str(path)), preview_excerpt=output[:200])

    if sink in INBOX_SINKS:
        return SinkResult(
            sink=sink,
            approval=ApprovalRef(event_id=str(uuid4()), inbox=sink),
        )

    raise ValueError(f"unknown sink {sink!r}")


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-") or "profile"
