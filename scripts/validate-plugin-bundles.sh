#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="${REPO_ROOT}" node <<'NODE'
const fs = require('fs');
const path = require('path');
const root = process.env.REPO_ROOT;
for (const rel of ['.codex-plugin/plugin.json','commands/ralph-start.md','commands/ralph-status.md','commands/ralph-stop.md','commands/ralph-add-context.md','skills/ralph-loop/SKILL.md','scripts/ralph-lib.js','scripts/ralph-start.js','scripts/ralph-runner.js','scripts/ralph-status.js','scripts/ralph-stop.js','scripts/ralph-add-context.js']) {
  if (!fs.existsSync(path.join(root, rel))) {
    console.error(`Missing required file: ${rel}`);
    process.exit(1);
  }
}
JSON.parse(fs.readFileSync(path.join(root, '.codex-plugin/plugin.json'), 'utf8'));
console.log('Plugin bundles validated.');
NODE
