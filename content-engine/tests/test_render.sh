#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT

"$ROOT/lib/render.sh" --profile general --dest "$OUT/general" --force >/dev/null

test -f "$OUT/general/SKILL.md"
test -f "$OUT/general/frontmatter.yaml"
test -f "$OUT/general/pipeline.md"
test -f "$OUT/general/platform-formatting.md"
test -f "$OUT/general/references/quality-checklist.md"
test -f "$OUT/general/voice-config.md"
test -f "$OUT/general/content-type-specs.md"

if grep -q '{{' "$OUT/general/SKILL.md"; then
  echo "unresolved template token in SKILL.md" >&2
  exit 1
fi

grep -q '^name: general$' "$OUT/general/SKILL.md"
grep -q 'frontmatter.yaml' "$OUT/general/SKILL.md"
