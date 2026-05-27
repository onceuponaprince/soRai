import json
from pathlib import Path

from content_engine_service.cli import main


ENGINE_ROOT = Path(__file__).resolve().parents[2] / "content-engine"


def test_cli_profiles(capsys):
    code = main(["profiles", "--engine-root", str(ENGINE_ROOT)])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["profiles"] == ["general"]


def test_cli_render(capsys):
    code = main(["render", "--engine-root", str(ENGINE_ROOT), "--profile", "general"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "general"
    assert payload["sink"] == "workspace-files"
    assert "frontmatter.yaml" in payload["rendered_files"]


def test_cli_run_with_mock_output(tmp_path, capsys):
    code = main(["run", "--engine-root", str(ENGINE_ROOT), "--artifact-root", str(tmp_path), "--profile", "general", "--brief", "write a note", "--mode", "stage", "--mock-output", "CLI final output"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["receipt_id"] == "mock"
    assert payload["artifact"]["path"]
    assert Path(payload["artifact"]["path"]).read_text() == "CLI final output"



def test_cli_run_with_store(tmp_path, capsys):
    store_path = tmp_path / "runs.sqlite3"
    code = main(["run", "--engine-root", str(ENGINE_ROOT), "--artifact-root", str(tmp_path / "artifacts"), "--store", str(store_path), "--profile", "general", "--brief", "write a note", "--mode", "stage", "--mock-output", "Stored CLI output"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)

    from content_engine_service.store import RunStore

    store = RunStore(store_path)
    stored = store.get_run(payload["run_id"])
    assert stored is not None
    assert stored.profile == "general"
    assert store.list_artifacts(payload["run_id"])



def test_cli_profiles_filters_by_role(capsys):
    code = main(["profiles", "--engine-root", str(ENGINE_ROOT), "--role", "operator"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["profiles"] == ["general"]


def test_cli_run_denies_profile_for_operator(tmp_path, capsys):
    code = main(["run", "--engine-root", str(ENGINE_ROOT), "--artifact-root", str(tmp_path), "--role", "operator", "--profile", "build-in-public", "--brief", "note", "--mock-output", "draft"])

    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert "not allowed" in payload["error"]


def test_cli_run_allows_profile_for_approver(tmp_path, capsys):
    code = main(["run", "--engine-root", str(ENGINE_ROOT), "--artifact-root", str(tmp_path), "--role", "approver", "--profile", "build-in-public", "--brief", "note", "--mode", "stage", "--mock-output", "draft"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["approval"]["inbox"] == "borai-inbox"
