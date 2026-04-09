#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
"${REPO_ROOT}/tests/test-ralph-plugin-bundle.sh"
"${REPO_ROOT}/tests/test-ralph-status.sh"
"${REPO_ROOT}/tests/test-ralph-loop.sh"
python3 -m unittest discover "${REPO_ROOT}/local/tests"
"${REPO_ROOT}/tests/test-install-codex.sh"
echo "All Ralph Wiggum Codex Plugin tests passed."
