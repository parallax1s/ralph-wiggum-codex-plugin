#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TMP_DIR="${REPO_ROOT}/tests/tmp/test-session-start-bridge"
HOME_DIR="${TMP_DIR}/home"
CODEX_HOME="${HOME_DIR}/.codex"
QUEUE_PATH="${CODEX_HOME}/thread-resumer-prompt-queue.json"
CONFIG_PATH="${CODEX_HOME}/config.toml"
UPSTREAM_HOOK="${TMP_DIR}/upstream-session-start.sh"

rm -rf "${TMP_DIR}"
mkdir -p "${CODEX_HOME}"

cat >"${CONFIG_PATH}" <<'EOF'
experimental_resume = "/tmp/resume-thread.jsonl"
EOF

cat >"${QUEUE_PATH}" <<'EOF'
{
  "thread-1": {
    "thread_id": "thread-1",
    "message": "continue",
    "title": "Thread One",
    "rollout_path": "/tmp/resume-thread.jsonl"
  }
}
EOF

cat >"${UPSTREAM_HOOK}" <<'EOF'
#!/usr/bin/env bash
cat <<'JSON'
{
  "additional_context": "base context"
}
JSON
EOF
chmod +x "${UPSTREAM_HOOK}"

OUTPUT="$(
  HOME="${HOME_DIR}" \
  CODEX_HOME="${CODEX_HOME}" \
  RALPH_UPSTREAM_SESSION_START="${UPSTREAM_HOOK}" \
  node "${REPO_ROOT}/hooks/session-start-bridge.js"
)"

echo "${OUTPUT}" | grep -F '"additional_context": "base context'
echo "${OUTPUT}" | grep -F 'Queued loop prompt for this resumed thread: continue'

if grep -Fq 'thread-1' "${QUEUE_PATH}"; then
  echo "Queued prompt was not consumed" >&2
  exit 1
fi

echo "test-session-start-bridge.sh: ok"
