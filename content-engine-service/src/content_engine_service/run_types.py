from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RunMode(str, Enum):
    STAGE = "stage"
    DRY_RUN = "dry-run"


class BoundaryStatus(str, Enum):
    PASS = "pass"
    REJECT_EXPLICIT = "reject-explicit"
    REFUSE_AND_STOP = "refuse-and-stop"


@dataclass(frozen=True)
class BoundaryVerdict:
    status: BoundaryStatus
    detail: str


@dataclass(frozen=True)
class DispatchResult:
    output: str
    receipt_id: str | None = None


@dataclass(frozen=True)
class ArtifactRef:
    path: str
    content_type: str = "text/markdown"


@dataclass(frozen=True)
class ApprovalRef:
    event_id: str
    inbox: str
    approval_status: str = "pending"


@dataclass(frozen=True)
class SinkResult:
    sink: str
    artifact: ArtifactRef | None = None
    approval: ApprovalRef | None = None
    preview_excerpt: str | None = None


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    profile: str
    mode: RunMode
    receipt_id: str | None
    boundary: BoundaryVerdict
    sink_result: SinkResult
    generated_output: str
