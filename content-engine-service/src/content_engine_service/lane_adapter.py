from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from content_engine_service.run_types import DispatchResult

VALID_LANES = frozenset({"api", "cli", "browser"})


class LaneDispatchError(RuntimeError):
    """Raised when a lane runner fails or returns malformed output."""


@dataclass(frozen=True)
class LaneRequest:
    bundle: str
    inputs: dict
    lane: str
    tool: str
    provenance: str
    runner: Path
    timeout: int = 180


def build_prompt(bundle: str, inputs: dict) -> str:
    rendered_inputs = "\n".join(f"- {key}: {value}" for key, value in sorted(inputs.items()))
    return (
        "You are running a soRai content-engine skill. The rendered skill bundle below is authoritative.\n\n"
        "===== REQUEST INPUTS =====\n"
        f"{rendered_inputs}\n\n"
        "===== RENDERED SKILL BUNDLE =====\n"
        f"{bundle}\n"
    )


def dispatch(request: LaneRequest) -> DispatchResult:
    if request.lane not in VALID_LANES:
        raise ValueError(f"unknown lane {request.lane!r}; expected one of {sorted(VALID_LANES)}")
    if not request.runner.is_file():
        raise LaneDispatchError(f"runner not found: {request.runner}")

    prompt = build_prompt(request.bundle, request.inputs)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as prompt_file:
        prompt_file.write(prompt)
        prompt_path = Path(prompt_file.name)

    try:
        proc = subprocess.run(
            [
                "python3",
                str(request.runner),
                "--tool",
                request.tool,
                "--lane",
                request.lane,
                "--provenance",
                request.provenance,
                "--prompt-file",
                str(prompt_path),
                "--timeout",
                str(request.timeout),
            ],
            capture_output=True,
            text=True,
            timeout=request.timeout + 5,
        )
    except subprocess.TimeoutExpired as exc:
        raise LaneDispatchError(f"lane runner timed out after {request.timeout}s") from exc
    finally:
        prompt_path.unlink(missing_ok=True)

    if proc.returncode != 0:
        raise LaneDispatchError(f"lane runner exited {proc.returncode}: {proc.stderr[:500]}")

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise LaneDispatchError(f"lane runner returned non-json output: {proc.stdout[:200]!r}") from exc

    if data.get("dispatch_status") != "ok":
        detail = data.get("error") or data.get("detail") or proc.stderr[:500]
        raise LaneDispatchError(f"dispatch_status={data.get('dispatch_status')!r}: {detail}")

    output = data.get("output")
    if not isinstance(output, str) or not output.strip():
        raise LaneDispatchError("lane runner returned no output")

    receipt_id = data.get("receipt_id") or data.get("id")
    return DispatchResult(output=output, receipt_id=str(receipt_id) if receipt_id else None)
