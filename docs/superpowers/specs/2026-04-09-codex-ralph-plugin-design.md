# Codex Ralph Loop Plugin Design

## Goal

Build a Codex-native local plugin that brings the Ralph Wiggum loop workflow into the Codex app without trying to port Claude plugin behavior directly. The plugin should provide a clean Codex UX for starting, monitoring, and stopping an iterative `codex exec` loop in the current repository.

## Non-Goals

- Multi-agent support in v1
- Claude/Copilot/OpenCode support in v1
- In-process self-looping inside Codex UI internals
- Full parity with `open-ralph-wiggum`
- Task orchestration beyond a single optional tasks file

## Product Shape

The product is a Codex plugin plus a local runner.

- The Codex plugin provides user-facing commands and skill guidance.
- A separate local runner process owns the loop lifecycle.
- The runner writes state into a repo-local `.ralph/` directory.
- Commands read and mutate that state instead of trying to keep loop state inside the app.

This keeps the design aligned with how Codex plugins actually work: plugins are good at discoverability, commands, metadata, and local tooling integration; they are not a good place to build a persistent autonomous control loop by themselves.

## External Reference

`open-ralph-wiggum` is a useful reference and possible source of selected ideas, but it should not be copied wholesale into the plugin.

Worth reusing conceptually:
- repo-local `.ralph` state files
- completion and abort promises
- status and add-context operations
- optional tasks mode

Not worth adopting directly in v1:
- Bun runtime dependency
- multi-agent abstractions
- cross-agent generic CLI contract
- direct dependence on non-Codex agent behavior

## Recommended Architecture

### Plugin Layer

Plugin root:
- `.codex-plugin/plugin.json`
- `commands/`
- `skills/ralph-loop/`
- `scripts/`

Plugin responsibilities:
- expose commands
- validate user input
- launch the runner
- read status from `.ralph`
- explain safe usage patterns

### Runner Layer

The runner is a local Node script started by the plugin.

Runner responsibilities:
- launch iterative `codex exec` runs
- persist state after every iteration
- detect completion/abort conditions
- support explicit stop requests
- append context between iterations
- guard against duplicate concurrent loops in the same repo

The runner should be a normal detached process, not a background shell one-liner.

## V1 Commands

### `/ralph-start`

Starts a loop in the current repository.

Inputs:
- task prompt
- max iterations
- optional model
- completion promise text
- optional abort promise text
- optional tasks mode flag

Behavior:
- refuse to start if another loop is already active in the repo unless forced
- create `.ralph/` if missing
- write initial loop state
- spawn detached runner
- report PID, state path, and first-step guidance

### `/ralph-status`

Shows the current loop status.

Outputs:
- running or stopped
- PID if present
- iteration count
- last iteration result
- completion or stop reason
- current task if tasks mode enabled
- last error if any

### `/ralph-stop`

Stops the loop cleanly.

Behavior:
- mark stop requested in state
- terminate runner if alive
- report final state

### `/ralph-add-context`

Appends additional operator guidance for future iterations.

Behavior:
- append to `.ralph/ralph-context.md`
- timestamp the entry
- report success and file path

## Repo State Layout

Each target repo gets a `.ralph/` directory.

Files:
- `.ralph/ralph-loop.state.json`
- `.ralph/ralph-history.json`
- `.ralph/ralph-context.md`
- `.ralph/ralph-tasks.md`
- `.ralph/logs/iteration-<n>.log`

### `ralph-loop.state.json`

Tracks live loop state.

Fields:
- `version`
- `status` (`idle`, `running`, `completed`, `aborted`, `stopped`, `failed`)
- `pid`
- `cwd`
- `startedAt`
- `updatedAt`
- `iteration`
- `maxIterations`
- `completionPromise`
- `abortPromise`
- `model`
- `taskPrompt`
- `tasksMode`
- `currentTask`
- `stopRequested`
- `lastExitCode`
- `lastResult`
- `lastError`

### `ralph-history.json`

Append-only-ish iteration history.

Each entry should include:
- iteration number
- start time
- end time
- exit code
- completion detected
- abort detected
- log path

### `ralph-context.md`

Human-injected steering context. The runner reads it before each new iteration.

### `ralph-tasks.md`

Optional structured task list for v1 tasks mode.

## Loop Execution Model

Each iteration should construct a prompt from:
- the original task
- completion contract
- optional abort contract
- current `.ralph/ralph-context.md`
- current task, if tasks mode is enabled
- a short instruction to inspect the current repo state and continue from existing work

Execution command:
- `codex exec <prompt>`
- optional `--model <model>`
- optional automation flags if explicitly chosen later

Completion detection:
- loop stops when output contains the configured completion promise marker
- loop aborts when output contains the configured abort promise marker
- loop fails when runner errors irrecoverably
- loop stops when max iterations reached
- loop stops when explicit stop requested

## Safety Model

### Required safeguards

- one active loop per repo by default
- explicit max iteration bound in v1
- persisted PID and liveness checks
- explicit stop signal support
- state written after every iteration
- logs preserved per iteration

### Out of scope for v1 but desirable later

- ACC lease awareness
- automatic test policy configuration
- branch isolation per loop
- model rotation
- approval-policy customization

## UX Notes

- Commands should be intentionally narrow.
- Status should be readable without opening raw JSON.
- The plugin should never imply the loop is inside Codex itself; it is a managed local runner for Codex.
- Error messages should point to `.ralph` files and exact next actions.

## Runtime Choice

Use Node, not Bun, for the first Codex-native implementation.

Reasons:
- better fit with the rest of the local plugin/runtime work in this repo
- fewer machine prerequisites
- simpler integration with current scripts and tests
- avoids making Bun a hidden dependency for plugin install

## Testing Strategy

### Unit-level

- state initialization
- prompt construction
- completion detection
- abort detection
- duplicate-loop refusal
- stop-request handling

### Integration-level

- start a loop in a temp repo using a fake Codex binary
- verify state transitions across iterations
- verify logs and history written correctly
- verify status command output
- verify add-context is consumed next iteration
- verify stop terminates cleanly

## V1 Success Criteria

The plugin is successful when a user can:
1. install it in Codex
2. run `/ralph-start` in a repo
3. see a detached Codex loop progress through iterations
4. inspect progress with `/ralph-status`
5. steer it with `/ralph-add-context`
6. stop it with `/ralph-stop`

without needing external CLIs beyond Codex itself and the local plugin runtime.

## Follow-on Versions

### V2
- tasks mode refinement
- model rotation
- configurable test/check hooks
- better log summarization

### V3
- ACC integration for shared repos
- optional Claude/OpenCode backends
- richer UI metadata and screenshots
