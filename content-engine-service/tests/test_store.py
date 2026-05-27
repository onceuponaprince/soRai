from content_engine_service.run_types import BoundaryStatus, BoundaryVerdict, RunMode, SinkResult, ArtifactRef, ApprovalRef
from content_engine_service.store import RunStore


def test_store_records_run_artifact_and_approval(tmp_path):
    store = RunStore(tmp_path / "runs.sqlite3")
    store.init_schema()
    boundary = BoundaryVerdict(BoundaryStatus.PASS, "ok")

    store.record_run(run_id="run-1", profile="general", mode=RunMode.STAGE, receipt_id="r1", boundary=boundary, sink="workspace-files")
    store.record_sink_result(run_id="run-1", profile="general", output="final", sink_result=SinkResult(sink="workspace-files", artifact=ArtifactRef(path="/tmp/out.md")))

    stored = store.get_run("run-1")
    assert stored is not None
    assert stored.profile == "general"
    assert stored.boundary_status == "pass"
    assert store.list_artifacts("run-1")[0]["path"] == "/tmp/out.md"

    store.record_run(run_id="run-2", profile="build-in-public", mode=RunMode.STAGE, receipt_id=None, boundary=boundary, sink="borai-inbox")
    store.record_sink_result(run_id="run-2", profile="build-in-public", output="draft", sink_result=SinkResult(sink="borai-inbox", approval=ApprovalRef(event_id="event-1", inbox="borai-inbox")))

    events = store.list_approval_events("run-2")
    assert events[0]["event_id"] == "event-1"
    assert events[0]["payload"] == {"profile": "build-in-public", "output": "draft"}



def test_store_signup_lifecycle_and_api_key_roles(tmp_path):
    store = RunStore(tmp_path / "runs.sqlite3")
    store.init_schema()

    signup = store.request_signup(email="person@example.com", requested_roles=("operator",))
    assert signup["status"] == "pending"

    approved = store.approve_signup(signup_id=signup["id"], approved_by="admin", approved_roles=("approver",), note="ok")
    assert approved["status"] == "approved"
    api_key = approved["api_key"]

    roles = store.roles_for_api_key(api_key)
    assert roles == ("approver",)
