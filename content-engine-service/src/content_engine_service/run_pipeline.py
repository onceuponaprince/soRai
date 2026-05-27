from __future__ import annotations

from pathlib import Path
from typing import Callable
from uuid import uuid4

from content_engine_service import boundary_validator, profiles_registry, sink_adapter
from content_engine_service.boundary_validator import BoundaryRejected
from content_engine_service.run_types import BoundaryStatus, DispatchResult, RunMode, RunRecord
from content_engine_service.store import RunStore

DispatchFn = Callable[[str, dict], DispatchResult]


class UnknownProfile(Exception):
    """Raised when the requested profile is absent from the engine root."""


def execute_pipeline(
    *,
    engine_root: Path,
    profile: str,
    inputs: dict,
    mode: RunMode,
    dispatch: DispatchFn,
    artifact_root: Path,
    render_cache: dict | None = None,
    store: RunStore | None = None,
) -> RunRecord:
    if profile not in profiles_registry.list_profile_names(engine_root):
        raise UnknownProfile(profile)

    bundle = profiles_registry.render_bundle(engine_root, profile, cache=render_cache)
    dispatch_result = dispatch(bundle.text, inputs)
    verdict = boundary_validator.validate(dispatch_result.output, profile)
    if verdict.status is not BoundaryStatus.PASS:
        raise BoundaryRejected(verdict)

    run_id = str(uuid4())
    if store is not None:
        store.init_schema()
        store.record_run(
            run_id=run_id,
            profile=profile,
            mode=mode,
            receipt_id=dispatch_result.receipt_id,
            boundary=verdict,
            sink=bundle.profile.sink,
        )

    sink_result = sink_adapter.route(
        sink=bundle.profile.sink,
        output=dispatch_result.output,
        profile=profile,
        mode=mode,
        run_id=run_id,
        artifact_root=artifact_root,
    )
    if store is not None:
        store.record_sink_result(
            run_id=run_id,
            profile=profile,
            output=dispatch_result.output,
            sink_result=sink_result,
        )

    return RunRecord(
        run_id=run_id,
        profile=profile,
        mode=mode,
        receipt_id=dispatch_result.receipt_id,
        boundary=verdict,
        sink_result=sink_result,
        generated_output=dispatch_result.output,
    )
