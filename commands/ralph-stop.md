---
description: Stop the current Ralph loop for this repository.
allowed-tools: [Read, Bash]
---

# Ralph Stop

1. Resolve the installed Ralph skill directory:

```bash
RALPH_SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/ralph-wiggum-codex-plugin"
RALPH_PLUGIN_ROOT="$(cd "${RALPH_SKILL_DIR}/../.." && pwd)"
```

2. Run:

```bash
node "${RALPH_PLUGIN_ROOT}/scripts/ralph-stop.js"
```
