---
description: Add operator guidance for future Ralph iterations in this repository.
argument-hint: <message>
allowed-tools: [Read, Bash]
---

# Ralph Add Context

1. Treat `$ARGUMENTS` as the context message. If it is empty, stop and ask for the message.
2. Resolve the installed Ralph skill directory:

```bash
RALPH_SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/ralph-wiggum-codex-plugin"
RALPH_PLUGIN_ROOT="$(cd "${RALPH_SKILL_DIR}/../.." && pwd)"
```

3. Run:

```bash
node "${RALPH_PLUGIN_ROOT}/scripts/ralph-add-context.js" --message "$ARGUMENTS"
```
