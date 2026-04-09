#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TMP_DIR="${REPO_ROOT}/tests/tmp/test-ralph-loop"
PROJECT_DIR="${TMP_DIR}/project"
LOG_FILE="${TMP_DIR}/fake-codex.log"

rm -rf "${TMP_DIR}"
mkdir -p "${PROJECT_DIR}"

set +e
RALPH_CODEX_BINARY="${REPO_ROOT}/scripts/fake-codex.sh" \
FAKE_CODEX_LOG="${LOG_FILE}" \
node "${REPO_ROOT}/scripts/ralph-start.js" \
  --prompt "Create hello.txt and output COMPLETE when done." \
  --max-iterations 2 \
  --completion-promise COMPLETE \
  >"${TMP_DIR}/stdout.log" 2>"${TMP_DIR}/stderr.log"
STATUS=$?
set -e

if [[ "${STATUS}" -eq 0 ]]; then
  echo "Expected Ralph start to fail before implementation exists" >&2
  exit 1
fi

grep -Eq 'ralph-start\.js|MODULE_NOT_FOUND|Cannot find module' "${TMP_DIR}/stderr.log"

echo "test-ralph-loop.sh: ok"
