#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT

"$ROOT/lib/render.sh" --profile build-in-public --dest "$OUT/bip" --force >/dev/null

python3 - "$OUT/bip/frontmatter.yaml" <<'PY'
from __future__ import annotations

import sys

path = sys.argv[1]
text = open(path).read()

required = [
    'name: "build-in-public"',
    'summary: "Build-in-public drafts in a fixed voice, staged for approval."',
    'sink: "borai-inbox"',
    'approval_required: true',
    'graph_query: "on"',
]

missing = [line for line in required if line not in text]
if missing:
    raise SystemExit("frontmatter missing: " + ", ".join(missing))
PY
