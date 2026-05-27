from __future__ import annotations

from pathlib import Path
from typing import Any


class FrontmatterError(RuntimeError):
    """Raised when rendered profile metadata is missing or malformed."""


def parse_frontmatter_yaml(text: str) -> dict[str, Any]:
    """Parse the small YAML subset emitted by content-engine.

    This intentionally supports only the shapes the renderer writes:
    quoted scalar values, booleans, one-level lists, and one-level maps.
    Keeping the parser narrow avoids a runtime dependency before the API layer.
    """
    result: dict[str, Any] = {}
    lines = text.splitlines()
    index = 0

    while index < len(lines):
        raw = lines[index]
        index += 1
        if not raw.strip():
            continue
        if raw.startswith("  "):
            raise FrontmatterError(f"unexpected indented line: {raw!r}")
        if ":" not in raw:
            raise FrontmatterError(f"invalid line: {raw!r}")

        key, value = raw.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise FrontmatterError(f"empty key in line: {raw!r}")

        if value:
            result[key] = _parse_scalar(value)
            continue

        children: list[str] = []
        while index < len(lines) and lines[index].startswith("  "):
            children.append(lines[index])
            index += 1

        if all(child.strip().startswith("- ") for child in children):
            result[key] = [_parse_scalar(child.strip()[2:].strip()) for child in children]
        else:
            mapping: dict[str, Any] = {}
            for child in children:
                child_text = child.strip()
                if ":" not in child_text:
                    raise FrontmatterError(f"invalid nested line: {child!r}")
                child_key, child_value = child_text.split(":", 1)
                mapping[child_key.strip()] = _parse_scalar(child_value.strip())
            result[key] = mapping

    return result


def load_frontmatter(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FrontmatterError(f"frontmatter.yaml not found: {path}")
    data = parse_frontmatter_yaml(path.read_text())
    for key in ("name", "summary", "sink", "content_types", "safety"):
        if key not in data:
            raise FrontmatterError(f"frontmatter missing required key: {key}")
    return data


def _parse_scalar(value: str) -> Any:
    if value == "true":
        return True
    if value == "false":
        return False
    if value == "[]":
        return []
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return value
