from pathlib import Path

import pytest

from content_engine_service.boundary_validator import BoundaryRejected
from content_engine_service.run_pipeline import execute_pipeline
from content_engine_service.run_types import DispatchResult, RunMode


ENGINE_ROOT = Path(__file__).resolve().parents[2] / "content-engine"


def test_pipeline_dry_run_does_not_write_artifact(tmp_path):
    def dispatch(bundle: str, inputs: dict) -> DispatchResult:
        assert "frontmatter.yaml" in bundle
        assert inputs["brief"] == "write a note"
        return DispatchResult(output="Draft output", receipt_id="receipt-1")

    record = execute_pipeline(
        engine_root=ENGINE_ROOT,
        profile="general",
        inputs={"brief": "write a note"},
        mode=RunMode.DRY_RUN,
        dispatch=dispatch,
        artifact_root=tmp_path,
    )

    assert record.receipt_id == "receipt-1"
    assert record.sink_result.artifact is None
    assert record.sink_result.preview_excerpt == "Draft output"
    assert not list(tmp_path.rglob("*.md"))


def test_pipeline_stage_writes_workspace_artifact(tmp_path):
    record = execute_pipeline(
        engine_root=ENGINE_ROOT,
        profile="general",
        inputs={"brief": "write a note"},
        mode=RunMode.STAGE,
        dispatch=lambda bundle, inputs: DispatchResult(output="Final output"),
        artifact_root=tmp_path,
    )

    assert record.sink_result.artifact is not None
    path = Path(record.sink_result.artifact.path)
    assert path.read_text() == "Final output"
    assert path.parent.name == "general"


def test_pipeline_stage_creates_approval_for_inbox_sink(tmp_path):
    record = execute_pipeline(
        engine_root=ENGINE_ROOT,
        profile="build-in-public",
        inputs={"brief": "launch note"},
        mode=RunMode.STAGE,
        dispatch=lambda bundle, inputs: DispatchResult(output="Approval draft"),
        artifact_root=tmp_path,
    )

    assert record.sink_result.approval is not None
    assert record.sink_result.approval.inbox == "borai-inbox"
    assert record.sink_result.artifact is None


def test_pipeline_rejects_boundary_before_sink(tmp_path):
    with pytest.raises(BoundaryRejected):
        execute_pipeline(
            engine_root=ENGINE_ROOT,
            profile="general",
            inputs={"brief": "write a note"},
            mode=RunMode.STAGE,
            dispatch=lambda bundle, inputs: DispatchResult(output="__BOUNDARY_FAIL__"),
            artifact_root=tmp_path,
        )

    assert not list(tmp_path.rglob("*"))



def test_pipeline_persists_records_when_store_is_provided(tmp_path):
    from content_engine_service.store import RunStore

    store = RunStore(tmp_path / "runs.sqlite3")
    record = execute_pipeline(
        engine_root=ENGINE_ROOT,
        profile="general",
        inputs={"brief": "write a note"},
        mode=RunMode.STAGE,
        dispatch=lambda bundle, inputs: DispatchResult(output="Persisted output", receipt_id="persist-receipt"),
        artifact_root=tmp_path / "artifacts",
        store=store,
    )

    stored = store.get_run(record.run_id)
    assert stored is not None
    assert stored.receipt_id == "persist-receipt"
    assert stored.sink == "workspace-files"
    artifacts = store.list_artifacts(record.run_id)
    assert len(artifacts) == 1
    assert artifacts[0]["path"] == record.sink_result.artifact.path
