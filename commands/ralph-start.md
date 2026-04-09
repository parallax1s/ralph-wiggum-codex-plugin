---
description: Start a bounded Codex Ralph loop in the current repository.
argument-hint: <task prompt>
allowed-tools: [Read, Bash]
---

# Ralph Start

Start a Ralph loop for the current repository.

## Arguments

The user invoked this command with: $ARGUMENTS

## Instructions

1. Treat `$ARGUMENTS` as the task prompt. If it is empty, stop and ask the user for the prompt text.
2. Resolve the installed Ralph skill directory:

```bash
RALPH_SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/ralph-wiggum-codex-plugin"
```

3. Confirm that `${RALPH_SKILL_DIR}` exists, then resolve the plugin root:

```bash
RALPH_PLUGIN_ROOT="$(cd "${RALPH_SKILL_DIR}/../.." && pwd)"
```

4. Run the start command with the built-in fallback bound. This runs in the current conversation by default.

```bash
node "${RALPH_PLUGIN_ROOT}/scripts/ralph-start.js" \
  --prompt "$ARGUMENTS" \
  --completion-promise COMPLETE
```

5. Report the command result and remind the user they can use `/ralph-status`, `/ralph-add-context`, or `/ralph-stop`.

## Notes

- Add `--background` only when the user explicitly wants a detached loop.
- If `--max-iterations` is omitted, Ralph uses `256` as the safety bound, which is the practical default for “until stopped”.
