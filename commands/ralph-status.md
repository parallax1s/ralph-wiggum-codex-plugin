---
description: Show the current Ralph loop status for this repository.
allowed-tools: [Read, Bash]
---

# Ralph Status

1. Resolve the installed Ralph skill directory:

```bash
RALPH_SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/ralph-wiggum-codex-plugin"
RALPH_PLUGIN_ROOT="$(cd "${RALPH_SKILL_DIR}/../.." && pwd)"
```

2. Run:

```bash
node "${RALPH_PLUGIN_ROOT}/scripts/ralph-status.js"
```
