#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
"${REPO_ROOT}/scripts/validate-plugin-bundles.sh" >/dev/null
echo "test-ralph-plugin-bundle.sh: ok"
