# Codex Ralph Loop Plugin Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Codex-native local plugin that can start, monitor, steer, and stop a detached iterative `codex exec` loop in the current repository.

**Architecture:** The plugin will expose four user-facing commands and a focused skill, while a small local Node runner owns the actual loop lifecycle and persists repo-local state under `.ralph/`. Tests will drive the runner and command helpers first using a fake Codex binary so loop behavior is verified without depending on the real Codex CLI.

**Tech Stack:** Codex local plugin layout, Node.js scripts, Markdown command files, JSON state files, shell integration tests, existing repo install/validation scripts.

---

## File Map

### Plugin metadata and UX surface

- Modify: `.codex-plugin/plugin.json`
  - Add the Ralph plugin identity, descriptions, and capabilities.
- Create: `commands/ralph-start.md`
  - Starts a loop in the current repo.
- Create: `commands/ralph-status.md`
  - Reads and summarizes `.ralph` state.
- Create: `commands/ralph-stop.md`
  - Requests stop and terminates runner.
- Create: `commands/ralph-add-context.md`
  - Appends operator guidance to `.ralph/ralph-context.md`.
- Create: `skills/ralph-loop/SKILL.md`
  - Explains safe operational use of the Ralph workflow in Codex.

### Runner and state helpers

- Create: `scripts/ralph-lib.js`
  - Shared helpers for paths, state I/O, history/log writing, prompt construction, PID/liveness checks.
- Create: `scripts/ralph-runner.js`
  - Detached loop engine that iteratively runs `codex exec`.
- Create: `scripts/ralph-start.js`
  - CLI entrypoint used by `/ralph-start` to initialize state and spawn the runner.
- Create: `scripts/ralph-status.js`
  - CLI entrypoint used by `/ralph-status` to summarize current state.
- Create: `scripts/ralph-stop.js`
  - CLI entrypoint used by `/ralph-stop` to request stop and kill the runner if needed.
- Create: `scripts/ralph-add-context.js`
  - CLI entrypoint used by `/ralph-add-context` to append context.
- Create: `scripts/fake-codex.sh`
  - Test helper that simulates `codex exec` output across iterations.

### Tests and validation

- Create: `tests/test-ralph-plugin-bundle.sh`
  - Verifies plugin bundle contains the new command and skill payloads.
- Create: `tests/test-ralph-loop.sh`
  - End-to-end shell test against the fake Codex binary.
- Create: `tests/test-ralph-status.sh`
  - Status formatting / idle-running-completed cases.
- Modify: `scripts/validate-plugin-bundles.sh`
  - Include Ralph plugin files in bundle validation.
- Modify: `scripts/test.sh`
  - Add Ralph tests to the full suite.
- Modify: `README.md`
  - Document the Ralph Codex plugin and loop workflow.

---

## Chunk 1: State Model and Test Harness

### Task 1: Add a failing end-to-end test for loop state initialization and completion

**Files:**
- Create: `tests/test-ralph-loop.sh`
- Create: `scripts/fake-codex.sh`
- Reference: `docs/superpowers/specs/2026-04-09-codex-ralph-plugin-design.md`

- [ ] **Step 1: Write the failing shell test for a single successful loop**

```bash
#!/usr/bin/env bash
set -euo pipefail

# temp repo
# start ralph with fake codex
# assert .ralph/ralph-loop.state.json exists
# assert status becomes completed
# assert history has at least one entry
# assert iteration log exists
```

- [ ] **Step 2: Run the test to verify it fails because the Ralph scripts do not exist yet**

Run: `./tests/test-ralph-loop.sh`
Expected: FAIL with missing `scripts/ralph-start.js` or similar

- [ ] **Step 3: Add `scripts/fake-codex.sh` with deterministic fake output behavior**

```bash
#!/usr/bin/env bash
# Writes prompt args to a fixture log and emits configurable completion text.
```

- [ ] **Step 4: Re-run the test to confirm the failure is still at missing production code, not broken fixtures**

Run: `./tests/test-ralph-loop.sh`
Expected: FAIL due to missing Ralph implementation

- [ ] **Step 5: Commit the failing harness and fake codex helper**

```bash
git add tests/test-ralph-loop.sh scripts/fake-codex.sh
git commit -m "test: add Ralph loop harness"
```

### Task 2: Implement shared Ralph state/path helpers

**Files:**
- Create: `scripts/ralph-lib.js`
- Test: `tests/test-ralph-loop.sh`

- [ ] **Step 1: Implement repo-local path helpers for `.ralph/` files**

```js
function getRalphPaths(cwd) {
  return {
    root: path.join(cwd, ".ralph"),
    state: path.join(cwd, ".ralph", "ralph-loop.state.json"),
    history: path.join(cwd, ".ralph", "ralph-history.json"),
    context: path.join(cwd, ".ralph", "ralph-context.md"),
    tasks: path.join(cwd, ".ralph", "ralph-tasks.md"),
    logs: path.join(cwd, ".ralph", "logs"),
  };
}
```

- [ ] **Step 2: Add state initialization and atomic JSON write helpers**

```js
function createInitialState(options) {
  return {
    version: 1,
    status: "running",
    iteration: 0,
    stopRequested: false,
    ...options,
  };
}
```

- [ ] **Step 3: Add history append and log path helpers**

```js
function appendHistory(historyPath, entry) {
  const history = readJson(historyPath, []);
  history.push(entry);
  writeJson(historyPath, history);
}
```

- [ ] **Step 4: Run `./tests/test-ralph-loop.sh` and confirm it still fails later in the flow**

Expected: FAIL at missing start/runner implementation, not missing state helpers

- [ ] **Step 5: Commit the shared helper layer**

```bash
git add scripts/ralph-lib.js
git commit -m "feat: add Ralph state helpers"
```

---

## Chunk 2: Start Command and Detached Runner

### Task 3: Add a failing test for duplicate-loop refusal and prompt persistence

**Files:**
- Modify: `tests/test-ralph-loop.sh`
- Test: `tests/test-ralph-loop.sh`

- [ ] **Step 1: Extend the test to try starting a second loop in the same repo**

```bash
# after first start, invoke start again
# expect non-zero exit and a clear duplicate-loop error
```

- [ ] **Step 2: Add assertions that the task prompt and completion promise are stored in state**

```bash
# jq-like check via node or python over ralph-loop.state.json
```

- [ ] **Step 3: Run `./tests/test-ralph-loop.sh` to verify the new assertions fail**

Expected: FAIL because `ralph-start.js` does not exist yet

- [ ] **Step 4: Commit the expanded failing test**

```bash
git add tests/test-ralph-loop.sh
git commit -m "test: cover Ralph start invariants"
```

### Task 4: Implement `ralph-start.js` and `ralph-runner.js`

**Files:**
- Create: `scripts/ralph-start.js`
- Create: `scripts/ralph-runner.js`
- Modify: `scripts/ralph-lib.js`
- Test: `tests/test-ralph-loop.sh`

- [ ] **Step 1: Implement `ralph-start.js` argument parsing**

```js
// parse: --prompt, --max-iterations, --model, --completion-promise, --abort-promise, --tasks, --force
```

- [ ] **Step 2: Refuse to start if state says a live runner already exists**

```js
if (existing.status === "running" && isPidAlive(existing.pid)) {
  throw new Error("Ralph loop already running in this repository");
}
```

- [ ] **Step 3: Initialize `.ralph/` state and spawn detached runner**

```js
const child = spawn(process.execPath, [runnerPath], {
  cwd,
  detached: true,
  stdio: "ignore",
  env,
});
child.unref();
```

- [ ] **Step 4: Implement `ralph-runner.js` iteration loop**

```js
for (let iteration = state.iteration + 1; iteration <= state.maxIterations; iteration++) {
  // build prompt
  // run codex exec
  // write iteration log
  // update state/history
  // check completion/abort/stop
}
```

- [ ] **Step 5: Build the iteration prompt from state + optional context file**

```js
function buildIterationPrompt(state, contextText) {
  return [
    state.taskPrompt,
    `Output <promise>${state.completionPromise}</promise> when complete.`,
    contextText ? `Additional context:\n${contextText}` : "",
  ].filter(Boolean).join("\n\n");
}
```

- [ ] **Step 6: Run `./tests/test-ralph-loop.sh` until it passes**

Expected: PASS with completed state, non-empty history, and duplicate-loop refusal

- [ ] **Step 7: Commit the start and runner implementation**

```bash
git add scripts/ralph-start.js scripts/ralph-runner.js scripts/ralph-lib.js
git commit -m "feat: add Ralph start and runner flow"
```

---

## Chunk 3: Status, Stop, and Add-Context Commands

### Task 5: Add failing tests for status formatting, stop, and add-context

**Files:**
- Create: `tests/test-ralph-status.sh`
- Modify: `tests/test-ralph-loop.sh`

- [ ] **Step 1: Write a failing status test for idle/running/completed states**

```bash
# prepare minimal state files
# run scripts/ralph-status.js
# assert readable lines: Status:, Iteration:, Last result:
```

- [ ] **Step 2: Extend the loop test to append context and stop a running loop**

```bash
# invoke add-context
# assert .ralph/ralph-context.md contains timestamped content
# invoke stop
# assert state.status becomes stopped or stopRequested true before termination
```

- [ ] **Step 3: Run `./tests/test-ralph-status.sh && ./tests/test-ralph-loop.sh` and verify failure**

Expected: FAIL because status/stop/add-context scripts do not exist yet

- [ ] **Step 4: Commit the failing command tests**

```bash
git add tests/test-ralph-status.sh tests/test-ralph-loop.sh
git commit -m "test: cover Ralph status and stop commands"
```

### Task 6: Implement `ralph-status.js`, `ralph-stop.js`, and `ralph-add-context.js`

**Files:**
- Create: `scripts/ralph-status.js`
- Create: `scripts/ralph-stop.js`
- Create: `scripts/ralph-add-context.js`
- Modify: `scripts/ralph-lib.js`
- Test: `tests/test-ralph-status.sh`
- Test: `tests/test-ralph-loop.sh`

- [ ] **Step 1: Implement status summary output**

```js
console.log(`Status: ${state.status}`);
console.log(`Iteration: ${state.iteration}/${state.maxIterations}`);
if (state.lastResult) console.log(`Last result: ${state.lastResult}`);
```

- [ ] **Step 2: Implement add-context append behavior with timestamp prefix**

```js
appendFileSync(contextPath, `\n## ${new Date().toISOString()}\n${message}\n`);
```

- [ ] **Step 3: Implement stop-request flagging and best-effort process termination**

```js
state.stopRequested = true;
writeState(state);
if (isPidAlive(state.pid)) process.kill(state.pid, "SIGTERM");
```

- [ ] **Step 4: Ensure the runner checks `stopRequested` between iterations and updates final status**

```js
if (freshState.stopRequested) {
  freshState.status = "stopped";
  writeState(freshState);
  break;
}
```

- [ ] **Step 5: Run `./tests/test-ralph-status.sh && ./tests/test-ralph-loop.sh` until both pass**

Expected: PASS

- [ ] **Step 6: Commit the command implementations**

```bash
git add scripts/ralph-status.js scripts/ralph-stop.js scripts/ralph-add-context.js scripts/ralph-lib.js
git commit -m "feat: add Ralph status stop and context commands"
```

---

## Chunk 4: Codex Plugin Surface and Bundle Validation

### Task 7: Add failing bundle validation for Ralph plugin files

**Files:**
- Modify: `scripts/validate-plugin-bundles.sh`
- Create: `tests/test-ralph-plugin-bundle.sh`
- Test: `tests/test-ralph-plugin-bundle.sh`

- [ ] **Step 1: Write a failing bundle test that requires Ralph commands and skill files**

```bash
# run validate-plugin-bundles and assert ralph files are included
```

- [ ] **Step 2: Run `./tests/test-ralph-plugin-bundle.sh` and verify failure**

Expected: FAIL because Ralph command/skill files do not exist yet

- [ ] **Step 3: Commit the failing bundle test**

```bash
git add tests/test-ralph-plugin-bundle.sh scripts/validate-plugin-bundles.sh
git commit -m "test: require Ralph plugin bundle files"
```

### Task 8: Implement plugin manifest, commands, and skill

**Files:**
- Modify: `.codex-plugin/plugin.json`
- Create: `commands/ralph-start.md`
- Create: `commands/ralph-status.md`
- Create: `commands/ralph-stop.md`
- Create: `commands/ralph-add-context.md`
- Create: `skills/ralph-loop/SKILL.md`
- Modify: `scripts/validate-plugin-bundles.sh`
- Test: `tests/test-ralph-plugin-bundle.sh`

- [ ] **Step 1: Update `.codex-plugin/plugin.json` to describe the Ralph plugin**

```json
{
  "name": "codex-ralph-loop",
  "skills": "./skills/",
  "interface": {
    "displayName": "Codex Ralph Loop",
    "category": "Coding"
  }
}
```

- [ ] **Step 2: Add `commands/ralph-start.md` wired to `scripts/ralph-start.js`**

```md
Run `node <plugin-root>/scripts/ralph-start.js --prompt ...`
```

- [ ] **Step 3: Add status, stop, and add-context command files wired to their scripts**

- [ ] **Step 4: Add `skills/ralph-loop/SKILL.md` describing safe loop usage, iteration limits, and stop behavior**

- [ ] **Step 5: Extend `scripts/validate-plugin-bundles.sh` to require the Ralph files**

- [ ] **Step 6: Run `./tests/test-ralph-plugin-bundle.sh` until it passes**

Expected: PASS

- [ ] **Step 7: Commit the plugin surface**

```bash
git add .codex-plugin/plugin.json commands/ralph-*.md skills/ralph-loop/SKILL.md scripts/validate-plugin-bundles.sh tests/test-ralph-plugin-bundle.sh
git commit -m "feat: expose Ralph loop as a Codex plugin"
```

---

## Chunk 5: Docs and Full Verification

### Task 9: Update README and usage docs

**Files:**
- Modify: `README.md`
- Reference: `docs/superpowers/specs/2026-04-09-codex-ralph-plugin-design.md`

- [ ] **Step 1: Add a README section for Codex Ralph Loop**

```md
## Codex Ralph Loop

Use `/ralph-start` to launch a bounded iterative Codex loop in the current repository.
```

- [ ] **Step 2: Document `.ralph/` state files and command set**

- [ ] **Step 3: Document safety limits and stop workflow**

- [ ] **Step 4: Commit docs updates**

```bash
git add README.md
git commit -m "docs: document Codex Ralph loop plugin"
```

### Task 10: Run full verification and finish cleanly

**Files:**
- Verify: `tests/test-ralph-loop.sh`
- Verify: `tests/test-ralph-status.sh`
- Verify: `tests/test-ralph-plugin-bundle.sh`
- Verify: `scripts/test.sh`

- [ ] **Step 1: Run targeted Ralph tests**

Run: `./tests/test-ralph-loop.sh && ./tests/test-ralph-status.sh && ./tests/test-ralph-plugin-bundle.sh`
Expected: PASS

- [ ] **Step 2: Run the full suite**

Run: `./scripts/test.sh`
Expected: `All ACC Collaboration Runtime tests passed.` or equivalent full success output including Ralph tests

- [ ] **Step 3: Inspect `git status` and ensure only intended files changed**

Run: `git status --short`
Expected: clean working tree after final commit

- [ ] **Step 4: Commit any final verification/doc fixes**

```bash
git add README.md scripts tests commands skills .codex-plugin/plugin.json
git commit -m "test: verify Codex Ralph loop plugin"
```

