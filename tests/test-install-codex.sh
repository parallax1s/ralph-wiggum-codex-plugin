#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TMP_DIR="${REPO_ROOT}/tests/tmp/test-install-codex"
CODEX_HOME="${TMP_DIR}/codex-home"
HOME_ROOT="${TMP_DIR}"
PLUGIN_DIR="${CODEX_HOME}/plugins/cache/local-codex-plugins/ralph-wiggum-codex-plugin/local"
SKILL_DIR="${CODEX_HOME}/skills/ralph-wiggum-codex-plugin"
CONFIG_PATH="${CODEX_HOME}/config.toml"
HOME_PLUGIN_LINK="${HOME_ROOT}/plugins/ralph-wiggum-codex-plugin"
MARKETPLACE_PATH="${HOME_ROOT}/.agents/plugins/marketplace.json"
HOOKS_DIR="${CODEX_HOME}/superpowers/hooks"
HOOKS_JSON="${HOOKS_DIR}/hooks.json"
rm -rf "${TMP_DIR}"
mkdir -p "${CODEX_HOME}" "${HOOKS_DIR}"
cat >"${HOOKS_JSON}" <<'EOF'
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" session-start",
            "async": false
          }
        ]
      }
    ]
  }
}
EOF
CODEX_HOME="${CODEX_HOME}" "${REPO_ROOT}/scripts/install-codex-plugin.sh" >/dev/null
[[ -L "${SKILL_DIR}" ]]
[[ "$(readlink "${SKILL_DIR}")" == "${REPO_ROOT}/skills/ralph-loop" ]]
[[ -L "${PLUGIN_DIR}" ]]
[[ "$(readlink "${PLUGIN_DIR}")" == "${REPO_ROOT}" ]]
[[ -L "${HOME_PLUGIN_LINK}" ]]
[[ "$(readlink "${HOME_PLUGIN_LINK}")" == "${REPO_ROOT}" ]]
[[ -f "${MARKETPLACE_PATH}" ]]
grep -F '[plugins."ralph-wiggum-codex-plugin@local-codex-plugins"]' "${CONFIG_PATH}" >/dev/null
grep -F 'enabled = true' "${CONFIG_PATH}" >/dev/null
grep -F "session-start-bridge.js" "${HOOKS_JSON}" >/dev/null
echo "test-install-codex.sh: ok"
