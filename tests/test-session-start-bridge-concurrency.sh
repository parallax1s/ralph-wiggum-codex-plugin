#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TMP_DIR="${REPO_ROOT}/tests/tmp/test-session-start-bridge-concurrency"
HOME_DIR="${TMP_DIR}/home"
CODEX_HOME="${HOME_DIR}/.codex"
QUEUE_PATH="${CODEX_HOME}/thread-resumer-prompt-queue.json"
CONFIG_PATH="${CODEX_HOME}/config.toml"
UPSTREAM_HOOK="${TMP_DIR}/upstream-session-start.sh"

rm -rf "${TMP_DIR}"
mkdir -p "${CODEX_HOME}"

cat >"${CONFIG_PATH}" <<'JSON'
experimental_resume = "/tmp/resume-thread.jsonl"
JSON

cat >"${QUEUE_PATH}" <<'JSON'
{
  "thread-1": {
    "thread_id": "thread-1",
    "message": "continue",
    "title": "Thread One",
    "rollout_path": "/tmp/resume-thread.jsonl"
  }
}
JSON

cat >"${UPSTREAM_HOOK}" <<'SH'
#!/usr/bin/env bash
cat <<'JSON'
{
  "additional_context": "base context"
}
JSON
SH
chmod +x "${UPSTREAM_HOOK}"

(
  HOME="${HOME_DIR}" CODEX_HOME="${CODEX_HOME}" RALPH_UPSTREAM_SESSION_START="${UPSTREAM_HOOK}" \
    node "${REPO_ROOT}/hooks/session-start-bridge.js" > "${TMP_DIR}/out1.json"
) &
PID1=$!
(
  HOME="${HOME_DIR}" CODEX_HOME="${CODEX_HOME}" RALPH_UPSTREAM_SESSION_START="${UPSTREAM_HOOK}" \
    node "${REPO_ROOT}/hooks/session-start-bridge.js" > "${TMP_DIR}/out2.json"
) &
PID2=$!
wait "$PID1"
wait "$PID2"

COUNT=$( (grep -F 'Queued loop prompt for this resumed thread: continue' "${TMP_DIR}/out1.json" || true; \
          grep -F 'Queued loop prompt for this resumed thread: continue' "${TMP_DIR}/out2.json" || true) | wc -l | tr -d ' ' )

if [[ "${COUNT}" != "1" ]]; then
  echo "Expected queued prompt to appear exactly once across concurrent session-start invocations; got ${COUNT}" >&2
  exit 1
fi

echo "test-session-start-bridge-concurrency.sh: ok"
