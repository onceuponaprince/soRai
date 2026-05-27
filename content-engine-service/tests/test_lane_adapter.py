from pathlib import Path

import pytest

from content_engine_service.lane_adapter import LaneDispatchError, LaneRequest, build_prompt, dispatch


FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_build_prompt_includes_inputs_and_bundle():
    prompt = build_prompt("BUNDLE", {"brief": "hello", "mode": "dry-run"})

    assert "soRai content-engine skill" in prompt
    assert "- brief: hello" in prompt
    assert "- mode: dry-run" in prompt
    assert "BUNDLE" in prompt


def test_dispatch_with_fake_runner():
    result = dispatch(LaneRequest(bundle="BUNDLE", inputs={"brief": "hello"}, lane="api", tool="test-tool", provenance="test", runner=FIXTURES / "fake_runner.py", timeout=10))

    assert result.receipt_id == "fake-receipt"
    assert "runner output via api/test-tool" in result.output


def test_dispatch_rejects_unknown_lane():
    with pytest.raises(ValueError):
        dispatch(LaneRequest(bundle="BUNDLE", inputs={}, lane="bad", tool="test", provenance="test", runner=FIXTURES / "fake_runner.py"))


def test_dispatch_rejects_missing_runner():
    with pytest.raises(LaneDispatchError):
        dispatch(LaneRequest(bundle="BUNDLE", inputs={}, lane="api", tool="test", provenance="test", runner=FIXTURES / "missing.py"))
