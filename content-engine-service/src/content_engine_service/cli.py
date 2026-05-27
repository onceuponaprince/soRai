from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from content_engine_service import profiles_registry
from content_engine_service.access_policy import Actor, AccessPolicy, ProfileAccessDenied
from content_engine_service.lane_adapter import LaneDispatchError, LaneRequest, dispatch as lane_dispatch
from content_engine_service.run_pipeline import UnknownProfile, execute_pipeline
from content_engine_service.run_types import DispatchResult, RunMode
from content_engine_service.store import RunStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sorai-content-engine-service")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("profiles", help="List available profiles")
    list_parser.add_argument("--engine-root", default=_default_engine_root())
    list_parser.add_argument("--role", action="append", default=[], help="Actor role used to filter profiles. Repeatable.")
    list_parser.add_argument("--allowlists", default="", help="Optional JSON allowlist policy path.")

    render_parser = subparsers.add_parser("render", help="Render a profile bundle summary")
    render_parser.add_argument("--profile", required=True)
    render_parser.add_argument("--engine-root", default=_default_engine_root())
    render_parser.add_argument("--role", action="append", default=[], help="Actor role used for profile access checks. Repeatable.")
    render_parser.add_argument("--allowlists", default="", help="Optional JSON allowlist policy path.")

    run_parser = subparsers.add_parser("run", help="Run a profile through the service pipeline")
    run_parser.add_argument("--profile", required=True)
    run_parser.add_argument("--brief", required=True)
    run_parser.add_argument("--mode", choices=[mode.value for mode in RunMode], default=RunMode.DRY_RUN.value)
    run_parser.add_argument("--engine-root", default=_default_engine_root())
    run_parser.add_argument("--artifact-root", default="artifacts")
    run_parser.add_argument("--runner", default="")
    run_parser.add_argument("--lane", default="api")
    run_parser.add_argument("--tool", default="router-qwen3.6")
    run_parser.add_argument("--timeout", type=int, default=180)
    run_parser.add_argument("--mock-output", default="", help="Bypass lane runner for local smoke tests.")
    run_parser.add_argument("--store", default="", help="Optional SQLite path for run records.")
    run_parser.add_argument("--role", action="append", default=[], help="Actor role used for profile access checks. Repeatable.")
    run_parser.add_argument("--allowlists", default="", help="Optional JSON allowlist policy path.")

    args = parser.parse_args(argv)

    try:
        if args.command == "profiles":
            names = profiles_registry.list_profile_names(Path(args.engine_root))
            policy = _load_policy(args.allowlists)
            actor = Actor.from_roles(args.role)
            print(json.dumps({"profiles": list(policy.allowed_profiles(actor, names)), "roles": list(actor.roles)}, indent=2))
            return 0

        if args.command == "render":
            names = profiles_registry.list_profile_names(Path(args.engine_root))
            _load_policy(args.allowlists).assert_can_access(Actor.from_roles(args.role), args.profile, names)
            bundle = profiles_registry.render_bundle(Path(args.engine_root), args.profile, cache={})
            print(json.dumps({"profile": bundle.profile.name, "summary": bundle.profile.summary, "sink": bundle.profile.sink, "rendered_files": list(bundle.rendered_files)}, indent=2))
            return 0

        if args.command == "run":
            names = profiles_registry.list_profile_names(Path(args.engine_root))
            _load_policy(args.allowlists).assert_can_access(Actor.from_roles(args.role), args.profile, names)

            if args.mock_output:
                dispatch_fn = lambda bundle, inputs: DispatchResult(output=args.mock_output, receipt_id="mock")
            else:
                if not args.runner:
                    raise SystemExit("--runner is required unless --mock-output is supplied")

                def dispatch_fn(bundle: str, inputs: dict) -> DispatchResult:
                    return lane_dispatch(LaneRequest(bundle=bundle, inputs=inputs, lane=args.lane, tool=args.tool, provenance=f"cli-run profile={args.profile}", runner=Path(args.runner), timeout=args.timeout))

            store = RunStore(args.store) if args.store else None
            record = execute_pipeline(engine_root=Path(args.engine_root), profile=args.profile, inputs={"brief": args.brief}, mode=RunMode(args.mode), dispatch=dispatch_fn, artifact_root=Path(args.artifact_root), store=store)
            print(json.dumps({"run_id": record.run_id, "profile": record.profile, "mode": record.mode.value, "receipt_id": record.receipt_id, "boundary": {"status": record.boundary.status.value, "detail": record.boundary.detail}, "sink": record.sink_result.sink, "artifact": None if record.sink_result.artifact is None else {"path": record.sink_result.artifact.path}, "approval": None if record.sink_result.approval is None else {"event_id": record.sink_result.approval.event_id, "inbox": record.sink_result.approval.inbox, "approval_status": record.sink_result.approval.approval_status}, "preview_excerpt": record.sink_result.preview_excerpt}, indent=2))
            return 0
    except (UnknownProfile, LaneDispatchError, ProfileAccessDenied) as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 1

    return 2


def _load_policy(path: str) -> AccessPolicy:
    if path:
        return AccessPolicy.from_json_file(path)
    return AccessPolicy.default()


def _default_engine_root() -> str:
    return os.environ.get("CONTENT_ENGINE_ROOT", str(Path(__file__).resolve().parents[3] / "content-engine"))


if __name__ == "__main__":
    raise SystemExit(main())
