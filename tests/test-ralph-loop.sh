#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TMP_DIR="${REPO_ROOT}/tests/tmp/test-ralph-loop"
LONG_REPO="${TMP_DIR}/long-running-project"
COMPLETE_REPO="${TMP_DIR}/completed-project"
LONG_LOG="${TMP_DIR}/long-fake-codex.log"
COMPLETE_LOG="${TMP_DIR}/complete-fake-codex.log"

wait_for_file() {
  local file_path="$1"
  local attempts="${2:-50}"
  local index=0
  while [[ "${index}" -lt "${attempts}" ]]; do
    if [[ -f "${file_path}" ]]; then
      return 0
    fi
    sleep 0.1
    index=$((index + 1))
  done
  echo "Timed out waiting for file: ${file_path}" >&2
  return 1
}

wait_for_state_status() {
  local state_path="$1"
  local expected_status="$2"
  local attempts="${3:-50}"
  local index=0
  while [[ "${index}" -lt "${attempts}" ]]; do
    if [[ -f "${state_path}" ]]; then
      local current_status
      current_status="$(STATE_PATH="${state_path}" node <<'EOF'
const fs = require("fs");
const state = JSON.parse(fs.readFileSync(process.env.STATE_PATH, "utf8"));
process.stdout.write(state.status || "");
EOF
)"
      if [[ "${current_status}" == "${expected_status}" ]]; then
        return 0
      fi
    fi
    sleep 0.1
    index=$((index + 1))
  done
  echo "Timed out waiting for status ${expected_status} in ${state_path}" >&2
  return 1
}

rm -rf "${TMP_DIR}"
mkdir -p "${LONG_REPO}" "${COMPLETE_REPO}"
printf 'repo\n' >"${LONG_REPO}/README.md"
printf 'repo\n' >"${COMPLETE_REPO}/README.md"

(
  cd "${LONG_REPO}"
  RALPH_CODEX_BINARY="${REPO_ROOT}/scripts/fake-codex.sh" \
  FAKE_CODEX_LOG="${LONG_LOG}" \
  FAKE_CODEX_MODE="sleep" \
  FAKE_CODEX_SLEEP_SECONDS="5" \
  node "${REPO_ROOT}/scripts/ralph-start.js" \
    --prompt "Stay running until stopped." \
    --max-iterations 1 \
    --completion-promise COMPLETE \
    >"${TMP_DIR}/long-start.stdout.log" 2>"${TMP_DIR}/long-start.stderr.log"
)

LONG_STATE="${LONG_REPO}/.ralph/ralph-loop.state.json"
wait_for_file "${LONG_STATE}"
wait_for_state_status "${LONG_STATE}" "running"

set +e
(
  cd "${LONG_REPO}"
  RALPH_CODEX_BINARY="${REPO_ROOT}/scripts/fake-codex.sh" \
  FAKE_CODEX_LOG="${LONG_LOG}" \
  FAKE_CODEX_MODE="sleep" \
  FAKE_CODEX_SLEEP_SECONDS="5" \
  node "${REPO_ROOT}/scripts/ralph-start.js" \
    --prompt "This second start should fail." \
    --max-iterations 1 \
    --completion-promise COMPLETE \
    >"${TMP_DIR}/duplicate.stdout.log" 2>"${TMP_DIR}/duplicate.stderr.log"
)
DUPLICATE_STATUS=$?
set -e

if [[ "${DUPLICATE_STATUS}" -eq 0 ]]; then
  echo "Expected duplicate Ralph start to fail" >&2
  exit 1
fi

grep -F "Ralph loop already running in this repository" "${TMP_DIR}/duplicate.stderr.log" >/dev/null

LONG_PID="$(STATE_PATH="${LONG_STATE}" node <<'EOF'
const fs = require("fs");
const state = JSON.parse(fs.readFileSync(process.env.STATE_PATH, "utf8"));
process.stdout.write(String(state.pid || ""));
EOF
)"

if [[ -n "${LONG_PID}" ]]; then
  kill "${LONG_PID}" 2>/dev/null || true
fi

(
  cd "${COMPLETE_REPO}"
  RALPH_CODEX_BINARY="${REPO_ROOT}/scripts/fake-codex.sh" \
  FAKE_CODEX_LOG="${COMPLETE_LOG}" \
  FAKE_CODEX_MODE="complete" \
  FAKE_CODEX_COMPLETE_PROMISE="COMPLETE" \
  node "${REPO_ROOT}/scripts/ralph-start.js" \
    --prompt "Create hello.txt and output COMPLETE when done." \
    --max-iterations 2 \
    --completion-promise COMPLETE \
    >"${TMP_DIR}/complete-start.stdout.log" 2>"${TMP_DIR}/complete-start.stderr.log"
)

COMPLETE_STATE="${COMPLETE_REPO}/.ralph/ralph-loop.state.json"
COMPLETE_HISTORY="${COMPLETE_REPO}/.ralph/ralph-history.json"

wait_for_file "${COMPLETE_STATE}"
wait_for_state_status "${COMPLETE_STATE}" "completed"
wait_for_file "${COMPLETE_HISTORY}"

COMPLETE_STATE="${COMPLETE_STATE}" \
COMPLETE_HISTORY="${COMPLETE_HISTORY}" \
node <<'EOF'
const fs = require("fs");
const path = require("path");

const state = JSON.parse(fs.readFileSync(process.env.COMPLETE_STATE, "utf8"));
const history = JSON.parse(fs.readFileSync(process.env.COMPLETE_HISTORY, "utf8"));

if (state.taskPrompt !== "Create hello.txt and output COMPLETE when done.") {
  process.exit(1);
}
if (state.completionPromise !== "COMPLETE") {
  process.exit(1);
}
if (state.iteration < 1 || state.lastResult !== "completed") {
  process.exit(1);
}
if (!Array.isArray(history) || history.length === 0) {
  process.exit(1);
}
const logPath = path.join(path.dirname(process.env.COMPLETE_STATE), "logs", `iteration-${state.iteration}.log`);
if (!fs.existsSync(logPath)) {
  process.exit(1);
}
EOF

grep -F "Create hello.txt and output COMPLETE when done." "${COMPLETE_LOG}" >/dev/null

echo "test-ralph-loop.sh: ok"
