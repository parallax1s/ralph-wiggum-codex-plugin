# Ralph Wiggum Codex Plugin

Ralph Wiggum Codex Plugin is a Codex-native local plugin for running bounded `codex exec` loops in the current repository.

It provides:

- `/ralph-start`
- `/ralph-status`
- `/ralph-add-context`
- `/ralph-stop`

It stores loop state under `.ralph/` in the target repository.

Default behavior:

- foreground loop in the current conversation
- optional detached mode when you pass `--background`

## Install

```bash
./scripts/install-codex-plugin.sh
```

This installer:

- symlinks the skill into `~/.codex/skills/ralph-wiggum-codex-plugin`
- symlinks the repo into `~/.codex/plugins/cache/local-codex-plugins/ralph-wiggum-codex-plugin/local`
- symlinks the repo into `~/plugins/ralph-wiggum-codex-plugin`
- enables `ralph-wiggum-codex-plugin@local-codex-plugins` in `~/.codex/config.toml`
- registers the plugin in `~/.agents/plugins/marketplace.json`

## Direct CLI Usage

```bash
node scripts/ralph-start.js --prompt "Implement feature X" --max-iterations 5 --completion-promise COMPLETE
node scripts/ralph-status.js
node scripts/ralph-add-context.js --message "Prefer the smaller patch."
node scripts/ralph-stop.js
```

## Validation

```bash
./scripts/test.sh
```

## App-native loop transport

The repo now carries a first app-native loop transport seam under `local/`.

Current first-slice behavior:

- queue one prompt for a target Codex thread with `queue_prompt_for_thread`
- consume that queued prompt exactly once with `consume_queued_prompt`
- combine prompt queueing, experimental resume staging, and optional app restart with `resume_thread_with_queue`

This intentionally avoids mutating Codex session transcript files directly. The queued prompt is stored in plugin-owned local state and is meant to be consumed by a future session-start hook or app integration point when the target thread opens.
