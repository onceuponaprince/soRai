from pathlib import Path

from content_engine_service.profiles_registry import list_profile_names, render_bundle


ENGINE_ROOT = Path(__file__).resolve().parents[2] / "content-engine"


def test_list_profile_names():
    assert list_profile_names(ENGINE_ROOT) == ["build-in-public", "general"]


def test_render_bundle_includes_frontmatter_and_skill():
    bundle = render_bundle(ENGINE_ROOT, "general", cache={})

    assert bundle.profile.name == "general"
    assert bundle.profile.summary == "Free-form written-content generation with caller-supplied voice."
    assert bundle.profile.sink == "workspace-files"
    assert "frontmatter.yaml" in bundle.rendered_files
    assert "SKILL.md" in bundle.rendered_files
    assert "===== FILE: frontmatter.yaml =====" in bundle.text
    assert "===== FILE: SKILL.md =====" in bundle.text
