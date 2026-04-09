#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TMP_DIR="${REPO_ROOT}/tests/tmp/test-ralph-status"
PROJECT_DIR="${TMP_DIR}/project"
STATE_PATH="${PROJECT_DIR}/.ralph/ralph-loop.state.json"

rm -rf "${TMP_DIR}"
mkdir -p "${PROJECT_DIR}/.ralph"

STATE_PATH="${STATE_PATH}" node <<'EOF'
const fs = require("fs");
const state = {
  version: 1,
  status: "completed",
  pid: 12345,
  cwd: process.cwd(),
  startedAt: "2026-04-09T00:00:00.000Z",
  updatedAt: "2026-04-09T00:00:01.000Z",
  iteration: 2,
  maxIterations: 5,
  completionPromise: "COMPLETE",
  abortPromise: null,
  model: null,
  taskPrompt: "Ship it.",
  tasksMode: false,
  currentTask: null,
  stopRequested: false,
  lastExitCode: 0,
  lastResult: "completed",
  lastError: null,
};
fs.writeFileSync(process.env.STATE_PATH, JSON.stringify(state, null, 2) + "\n");
EOF

OUTPUT="$(cd "${PROJECT_DIR}" && node "${REPO_ROOT}/scripts/ralph-status.js")"

grep -F "Status: completed" <<<"${OUTPUT}" >/dev/null
grep -F "Iteration: 2/5" <<<"${OUTPUT}" >/dev/null
grep -F "Last result: completed" <<<"${OUTPUT}" >/dev/null

echo "test-ralph-status.sh: ok"
