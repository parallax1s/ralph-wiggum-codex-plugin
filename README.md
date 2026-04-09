# Ralph Wiggum Codex Plugin

Ralph Wiggum Codex Plugin is a Codex-native local plugin for running bounded detached `codex exec` loops in the current repository.

It provides:

- `/ralph-start`
- `/ralph-status`
- `/ralph-add-context`
- `/ralph-stop`

It stores loop state under `.ralph/` in the target repository.

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
