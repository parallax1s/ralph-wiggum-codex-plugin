#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -P "${SCRIPT_DIR}/.." && pwd)"
TARGET_ROOT="${CODEX_HOME:-${HOME}/.codex}"
HOME_ROOT="$(cd "${TARGET_ROOT}/.." && pwd)"
SKILLS_DIR="${TARGET_ROOT}/skills"
PLUGIN_NAME="ralph-wiggum-codex-plugin"
PLUGIN_KEY="${PLUGIN_NAME}@local-codex-plugins"
TARGET_SKILL="${SKILLS_DIR}/${PLUGIN_NAME}"
PLUGIN_ROOT="${TARGET_ROOT}/plugins/cache/local-codex-plugins/${PLUGIN_NAME}"
PLUGIN_INSTALL="${PLUGIN_ROOT}/local"
CONFIG_PATH="${TARGET_ROOT}/config.toml"
MARKETPLACE_PATH="${HOME_ROOT}/.agents/plugins/marketplace.json"
HOME_PLUGIN_DIR="${HOME_ROOT}/plugins"
HOME_PLUGIN_LINK="${HOME_PLUGIN_DIR}/${PLUGIN_NAME}"
HOOKS_JSON_PATH="${TARGET_ROOT}/superpowers/hooks/hooks.json"
"${REPO_ROOT}/scripts/validate-plugin-bundles.sh" >/dev/null
mkdir -p "${SKILLS_DIR}" "${PLUGIN_ROOT}" "$(dirname "${MARKETPLACE_PATH}")" "${HOME_PLUGIN_DIR}"
rm -rf "${TARGET_SKILL}" && ln -s "${REPO_ROOT}/skills/ralph-loop" "${TARGET_SKILL}"
rm -rf "${PLUGIN_INSTALL}" && ln -s "${REPO_ROOT}" "${PLUGIN_INSTALL}"
rm -rf "${HOME_PLUGIN_LINK}" && ln -s "${REPO_ROOT}" "${HOME_PLUGIN_LINK}"
touch "${CONFIG_PATH}"
if ! grep -Fq "[plugins.\"${PLUGIN_KEY}\"]" "${CONFIG_PATH}"; then
  printf '\n[plugins."%s"]\nenabled = true\n' "${PLUGIN_KEY}" >>"${CONFIG_PATH}"
fi
MARKETPLACE_PATH="${MARKETPLACE_PATH}" PLUGIN_NAME="${PLUGIN_NAME}" node <<'NODE'
const fs = require('fs');
const path = require('path');
const p = process.env.MARKETPLACE_PATH;
const name = process.env.PLUGIN_NAME;
let data;
try { data = JSON.parse(fs.readFileSync(p, 'utf8')); } catch { data = { name: 'Local Plugins', interface: { displayName: 'Local Plugins' }, plugins: [] }; }
data.plugins = (data.plugins || []).filter((x) => x && x.name !== name);
data.plugins.push({ name, source: { source: 'local', path: `./plugins/${name}` }, policy: { installation: 'AVAILABLE', authentication: 'ON_INSTALL' }, category: 'Coding' });
fs.mkdirSync(path.dirname(p), { recursive: true });
fs.writeFileSync(p, JSON.stringify(data, null, 2) + '\n');
NODE

if [ -f "${HOOKS_JSON_PATH}" ]; then
  HOOKS_JSON_PATH="${HOOKS_JSON_PATH}" HOME_PLUGIN_LINK="${HOME_PLUGIN_LINK}" node <<'NODE'
const fs = require('fs');
const path = process.env.HOOKS_JSON_PATH;
const pluginPath = process.env.HOME_PLUGIN_LINK;
const desired = `node "${pluginPath}/hooks/session-start-bridge.js"`;
const data = JSON.parse(fs.readFileSync(path, 'utf8'));
const sessionStart = (((data || {}).hooks || {}).SessionStart || []);
for (const entry of sessionStart) {
  for (const hook of (entry.hooks || [])) {
    if (hook && hook.type === 'command') {
      hook.command = desired;
    }
  }
}
fs.writeFileSync(path, JSON.stringify(data, null, 2) + '\n');
NODE
fi
echo "Installed Codex skill at ${TARGET_SKILL}"
echo "Installed Codex local plugin at ${PLUGIN_INSTALL}"
echo "Registered home-local plugin at ${HOME_PLUGIN_LINK}"
echo "Enabled ${PLUGIN_KEY} in ${CONFIG_PATH}"
echo "Registered ${PLUGIN_NAME} in ${MARKETPLACE_PATH}"
