#!/usr/bin/env bash
set -euo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$TEST_DIR/test_render.sh"
"$TEST_DIR/test_frontmatter.sh"

echo "content-engine tests passed"
