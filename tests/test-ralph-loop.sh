#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TMP_DIR="${REPO_ROOT}/tests/tmp/test-ralph-loop"
LONG_REPO="${TMP_DIR}/long-running-project"
COMPLETE_REPO="${TMP_DIR}/completed-project"
LONG_LOG="${TMP_DIR}/long-fake-codex.log"
COMPLETE_LOG="${TMP_DIR}/complete-fake-codex.log"
FOREGROUND_REPO="${TMP_DIR}/foreground-project"
TIMEOUT_REPO="${TMP_DIR}/timeout-project"

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
mkdir -p "${LONG_REPO}" "${COMPLETE_REPO}" "${FOREGROUND_REPO}"
mkdir -p "${TIMEOUT_REPO}"
printf 'repo\n' >"${LONG_REPO}/README.md"
printf 'repo\n' >"${COMPLETE_REPO}/README.md"
printf 'repo\n' >"${FOREGROUND_REPO}/README.md"
printf 'repo\n' >"${TIMEOUT_REPO}/README.md"

(
  cd "${FOREGROUND_REPO}"
  RALPH_CODEX_BINARY="${REPO_ROOT}/scripts/fake-codex.sh" \
  FAKE_CODEX_MODE="complete" \
  FAKE_CODEX_COMPLETE_PROMISE="COMPLETE" \
  node "${REPO_ROOT}/scripts/ralph-start.js" \
    --prompt "Run in foreground by default." \
    --max-iterations 2 \
    --completion-promise COMPLETE \
    >"${TMP_DIR}/foreground.stdout.log" 2>"${TMP_DIR}/foreground.stderr.log"
)

FOREGROUND_STATE="${FOREGROUND_REPO}/.ralph/ralph-loop.state.json"
FOREGROUND_HISTORY="${FOREGROUND_REPO}/.ralph/ralph-history.json"
wait_for_file "${FOREGROUND_STATE}"
wait_for_state_status "${FOREGROUND_STATE}" "completed"
wait_for_file "${FOREGROUND_HISTORY}"

FOREGROUND_STATE="${FOREGROUND_STATE}" \
FOREGROUND_HISTORY="${FOREGROUND_HISTORY}" \
node <<'EOF'
const fs = require("fs");
const path = require("path");
const state = JSON.parse(fs.readFileSync(process.env.FOREGROUND_STATE, "utf8"));
const history = JSON.parse(fs.readFileSync(process.env.FOREGROUND_HISTORY, "utf8"));
if (state.lastResult !== "completed") {
  process.exit(1);
}
if (state.pid !== null) {
  process.exit(1);
}
if (!Array.isArray(history) || history.length === 0) {
  process.exit(1);
}
const logPath = path.join(path.dirname(process.env.FOREGROUND_STATE), "logs", `iteration-${state.iteration}.log`);
if (!fs.existsSync(logPath)) {
  process.exit(1);
}
EOF

(
  cd "${TIMEOUT_REPO}"
  RALPH_CODEX_BINARY="${REPO_ROOT}/scripts/fake-codex.sh" \
  FAKE_CODEX_MODE="sleep" \
  FAKE_CODEX_SLEEP_SECONDS="5" \
  node "${REPO_ROOT}/scripts/ralph-start.js" \
    --prompt "Timeout after one bounded iteration." \
    --max-iterations 1 \
    --iteration-timeout-ms 1000 \
    --completion-promise COMPLETE \
    >"${TMP_DIR}/timeout.stdout.log" 2>"${TMP_DIR}/timeout.stderr.log"
)

TIMEOUT_STATE="${TIMEOUT_REPO}/.ralph/ralph-loop.state.json"
TIMEOUT_HISTORY="${TIMEOUT_REPO}/.ralph/ralph-history.json"
wait_for_file "${TIMEOUT_STATE}"
wait_for_state_status "${TIMEOUT_STATE}" "failed"
wait_for_file "${TIMEOUT_HISTORY}"

TIMEOUT_STATE="${TIMEOUT_STATE}" \
TIMEOUT_HISTORY="${TIMEOUT_HISTORY}" \
node <<'EOF'
const fs = require("fs");
const history = JSON.parse(fs.readFileSync(process.env.TIMEOUT_HISTORY, "utf8"));
const state = JSON.parse(fs.readFileSync(process.env.TIMEOUT_STATE, "utf8"));
if (state.lastResult !== "iteration-timeout") {
  process.exit(1);
}
if (state.lastError !== "Codex iteration timed out after 1000ms") {
  process.exit(1);
}
if (!Array.isArray(history) || history.length !== 1) {
  process.exit(1);
}
if (history[0].timedOut !== true) {
  process.exit(1);
}
if (history[0].completionDetected !== false) {
  process.exit(1);
}
EOF

(
  cd "${LONG_REPO}"
  RALPH_CODEX_BINARY="${REPO_ROOT}/scripts/fake-codex.sh" \
  FAKE_CODEX_LOG="${LONG_LOG}" \
  FAKE_CODEX_MODE="sleep" \
  FAKE_CODEX_SLEEP_SECONDS="5" \
  node "${REPO_ROOT}/scripts/ralph-start.js" \
    --background \
    --prompt "Stay running until stopped." \
    --max-iterations 1 \
    --completion-promise COMPLETE \
    >"${TMP_DIR}/long-start.stdout.log" 2>"${TMP_DIR}/long-start.stderr.log"
)

LONG_STATE="${LONG_REPO}/.ralph/ralph-loop.state.json"
wait_for_file "${LONG_STATE}"
wait_for_state_status "${LONG_STATE}" "running"

LONG_PID="$(START_STDOUT="${TMP_DIR}/long-start.stdout.log" node <<'EOF'
const fs = require("fs");
const payload = JSON.parse(fs.readFileSync(process.env.START_STDOUT, "utf8"));
process.stdout.write(String(payload.pid || ""));
EOF
)"

set +e
(
  cd "${LONG_REPO}"
  RALPH_CODEX_BINARY="${REPO_ROOT}/scripts/fake-codex.sh" \
  FAKE_CODEX_LOG="${LONG_LOG}" \
  FAKE_CODEX_MODE="sleep" \
  FAKE_CODEX_SLEEP_SECONDS="5" \
  node "${REPO_ROOT}/scripts/ralph-start.js" \
    --background \
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

(
  cd "${LONG_REPO}"
  node "${REPO_ROOT}/scripts/ralph-add-context.js" \
    --message "The operator added more context." \
    >"${TMP_DIR}/add-context.stdout.log" 2>"${TMP_DIR}/add-context.stderr.log"
)

grep -F "The operator added more context." "${LONG_REPO}/.ralph/ralph-context.md" >/dev/null

(
  cd "${LONG_REPO}"
  node "${REPO_ROOT}/scripts/ralph-stop.js" \
    >"${TMP_DIR}/stop.stdout.log" 2>"${TMP_DIR}/stop.stderr.log"
)

wait_for_state_status "${LONG_STATE}" "stopped"

if [[ -n "${LONG_PID}" ]]; then
  if kill -0 "${LONG_PID}" 2>/dev/null; then
    echo "Expected Ralph stop to terminate the long-running process" >&2
    exit 1
  fi
fi

(
  cd "${COMPLETE_REPO}"
  RALPH_CODEX_BINARY="${REPO_ROOT}/scripts/fake-codex.sh" \
  FAKE_CODEX_LOG="${COMPLETE_LOG}" \
  FAKE_CODEX_MODE="complete" \
  FAKE_CODEX_COMPLETE_PROMISE="COMPLETE" \
  node "${REPO_ROOT}/scripts/ralph-start.js" \
    --background \
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
