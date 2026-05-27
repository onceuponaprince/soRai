#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PROFILE=""
DEST=""
OUT=""
FORCE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --profile) PROFILE="${2:-}"; shift 2 ;;
    --dest) DEST="${2:-}"; shift 2 ;;
    --out) OUT="${2:-}"; shift 2 ;;
    --force) FORCE=1; shift ;;
    *) echo "render.sh: unknown arg: $1" >&2; exit 2 ;;
  esac
done

[ -n "$PROFILE" ] || { echo "render.sh: --profile required" >&2; exit 2; }
[ -n "$DEST" ] || { echo "render.sh: --dest required" >&2; exit 2; }

PROF_DIR="$REPO_ROOT/profiles/$PROFILE"
[ -d "$PROF_DIR" ] || { echo "render.sh: no such profile: $PROFILE" >&2; exit 1; }
[ -f "$PROF_DIR/profile.toml" ] || { echo "render.sh: missing $PROF_DIR/profile.toml" >&2; exit 1; }

OUT_RESOLVED="${OUT:-${CONTENT_ENGINE_OUT:-$REPO_ROOT/content-out}}"

if [ -e "$DEST" ] && [ -n "$(ls -A "$DEST" 2>/dev/null || true)" ] && [ "$FORCE" -ne 1 ]; then
  echo "render.sh: dest not empty: $DEST (pass --force to overwrite)" >&2
  exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

python3 - "$REPO_ROOT" "$PROFILE" "$OUT_RESOLVED" "$TMP" <<'PY'
from __future__ import annotations

import pathlib
import re
import shutil
import sys
import tomllib

root = pathlib.Path(sys.argv[1])
profile = sys.argv[2]
out_dir = sys.argv[3]
tmp = pathlib.Path(sys.argv[4])
prof_dir = root / "profiles" / profile
cfg = tomllib.loads((prof_dir / "profile.toml").read_text())

version = (root / "VERSION").read_text().strip()
template = (root / "core" / "SKILL.template.md").read_text()

def yaml_scalar(value: object) -> str:
    text = str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'

def yaml_list(values: list[str]) -> str:
    if not values:
        return "[]"
    return "\n".join(f"  - {yaml_scalar(value)}" for value in values)

def required_string(key: str) -> str:
    value = cfg.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"render.sh: profile {profile!r} missing string {key!r}")
    return value.strip()

def required_string_list(key: str) -> list[str]:
    value = cfg.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise SystemExit(f"render.sh: profile {profile!r} missing string list {key!r}")
    return [item.strip() for item in value]

name = required_string("name")
summary = required_string("summary")
sink = required_string("sink")
voice_mode = required_string("voice")
graph_query = required_string("graph_query")
type_noun = required_string("type_noun")
type_spec_file = required_string("type_spec_file")
content_types = required_string_list("content_types")
references = required_string_list("references")
description = " ".join(required_string("triggers").split())

if voice_mode.startswith("fixed:"):
    voice_file = voice_mode.split(":", 1)[1]
    voice_instruction = (
        f"Before drafting anything, read `{voice_file}`. This is the non-negotiable voice source."
    )
else:
    voice_instruction = (
        "This profile has no built-in voice. The caller must supply a writing sample, named voice, "
        "or explicit voice direction. If no voice is supplied, stop and ask before drafting."
    )

graph_section = ""
if graph_query == "on":
    graph_section = (root / "core" / "graph-query.md").read_text().rstrip() + "\n\n"

sink_file = root / "core" / "sinks" / f"{sink}.md"
if not sink_file.is_file():
    raise SystemExit(f"render.sh: unknown sink {sink!r}")
sink_section = sink_file.read_text().replace("{{OUTPUT_DIR}}", str(out_dir)).rstrip() + "\n"

replacements = {
    "{{NAME}}": name,
    "{{DESCRIPTION}}": description,
    "{{VERSION}}": version,
    "{{TYPE_NOUN}}": type_noun,
    "{{TYPE_SPEC_FILE}}": type_spec_file,
    "{{CONTENT_TYPES}}": ", ".join(content_types),
    "{{VOICE_INSTRUCTION}}": voice_instruction,
    "{{GRAPH_QUERY_SECTION}}": graph_section,
    "{{SINK_SECTION}}": sink_section,
}

skill = template
for token, value in replacements.items():
    skill = skill.replace(token, value)

leftover = re.findall(r"\{\{[^}]+\}\}", skill)
if leftover:
    raise SystemExit("render.sh: unresolved tokens: " + ", ".join(sorted(set(leftover))))

tmp.mkdir(parents=True, exist_ok=True)
(tmp / "references").mkdir(parents=True, exist_ok=True)
(tmp / "SKILL.md").write_text(skill)

frontmatter = "\n".join(
    [
        f"name: {yaml_scalar(name)}",
        f"summary: {yaml_scalar(summary)}",
        f"description: {yaml_scalar(description)}",
        f"version: {yaml_scalar(version)}",
        f"profile: {yaml_scalar(profile)}",
        f"sink: {yaml_scalar(sink)}",
        f"type_noun: {yaml_scalar(type_noun)}",
        "content_types:",
        yaml_list(content_types),
        "inputs:",
        "  - \"brief\"",
        f"graph_query: {yaml_scalar(graph_query)}",
        "safety:",
        "  boundary_required: true",
        f"  approval_required: {'true' if sink in {'borai-inbox', 'borai-content-inbox'} else 'false'}",
        "",
    ]
)
(tmp / "frontmatter.yaml").write_text(frontmatter)

shutil.copy(root / "core" / "pipeline.md", tmp / "pipeline.md")
shutil.copy(root / "core" / "platform-formatting.md", tmp / "platform-formatting.md")
shutil.copy(root / "core" / "references" / "quality-checklist.md", tmp / "references" / "quality-checklist.md")

for ref in references:
    src = prof_dir / ref
    if not src.is_file():
        raise SystemExit(f"render.sh: declared reference missing: {src}")
    shutil.copy(src, tmp / ref)
PY

mkdir -p "$DEST"
find "$DEST" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
cp -R "$TMP"/. "$DEST"/
echo "rendered profile '$PROFILE' -> $DEST"
