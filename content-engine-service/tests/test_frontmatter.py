from content_engine_service.frontmatter import parse_frontmatter_yaml


def test_parse_frontmatter_yaml_subset():
    parsed = parse_frontmatter_yaml(
        '''name: "general"
summary: "Free-form"
necessary: true
content_types:
  - "essay"
  - "thread"
safety:
  boundary_required: true
  approval_required: false
'''
    )

    assert parsed["name"] == "general"
    assert parsed["necessary"] is True
    assert parsed["content_types"] == ["essay", "thread"]
    assert parsed["safety"]["boundary_required"] is True
    assert parsed["safety"]["approval_required"] is False
