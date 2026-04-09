# App-Native Loop Transport Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first working app-native loop transport that queues a prompt for a Codex thread, reopens that thread in the Codex app, and consumes the queued prompt once when the thread resumes.

**Architecture:** Extend the existing local thread-resumer plugin instead of mutating Codex session files directly. Store queued prompts in plugin-owned local state keyed by thread id, add an app-control/resume path that stages one queued prompt for a target thread, and wire a session-start consumption seam that can read and clear the queued prompt exactly once.

**Tech Stack:** Python MCP server for thread/app control, local JSON persistence, existing Codex desktop thread/session metadata, shell tests plus focused Python tests.

---

## File Map

- Modify: `local/server/main.py`
  - Add MCP tool definitions and handlers for queued prompt lifecycle and resume-with-queue orchestration.
- Modify: `local/server/models.py`
  - Add typed models for queued prompt records and response payloads if needed.
- Modify: `local/server/config_store.py` or create `local/server/prompt_queue_store.py`
  - Store queued prompts separately from Codex session files.
- Modify: `local/server/app_control.py`
  - Reuse app restart/focus behavior for resume-with-queue flow if needed.
- Modify: `local/server/thread_store.py`
  - Resolve thread identity and metadata for queue targeting.
- Modify or create: `local/tests/test_prompt_queue_store.py`
  - Cover queue write/read/clear semantics.
- Modify or create: `local/tests/test_app_native_loop_tools.py`
  - Cover queue/resume/consume tool behavior.
- Modify: `README.md`
  - Document the app-native loop flow and its limits.
- Optional small hook seam: a dedicated file under the plugin repo documenting or generating the session-start integration contract if direct hook wiring is possible in scope.

## Chunk 1: Queued Prompt Store

### Task 1: Add failing store tests

**Files:**
- Test: `local/tests/test_prompt_queue_store.py`
- Create/Modify: `local/server/prompt_queue_store.py`

- [ ] **Step 1: Write the failing test**

Cover:
- queue one prompt for one thread
- read queued prompt back
- clear queued prompt
- consume-once semantics return the prompt once and then remove it

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest local/tests/test_prompt_queue_store.py -q`
Expected: FAIL on missing module or missing behavior

- [ ] **Step 3: Write minimal implementation**

Implement a small JSON-backed store keyed by `thread_id` with:
- `queue_prompt(thread_id, message, metadata?)`
- `peek_prompt(thread_id)`
- `consume_prompt(thread_id)`
- `clear_prompt(thread_id)`

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest local/tests/test_prompt_queue_store.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add local/server/prompt_queue_store.py local/tests/test_prompt_queue_store.py
git commit -m "add queued prompt store for app loop"
```

## Chunk 2: MCP Tools for Queue/Consume/Resume

### Task 2: Add failing MCP tool tests

**Files:**
- Modify: `local/server/main.py`
- Test: `local/tests/test_app_native_loop_tools.py`
- Reference: `local/server/thread_store.py`, `local/server/app_control.py`

- [ ] **Step 1: Write the failing test**

Cover tools:
- `queue_prompt_for_thread`
- `consume_queued_prompt`
- `resume_thread_with_queue`

Behavior:
- queue tool validates thread exists and stores prompt
- consume tool returns prompt once, then clears it
- resume-with-queue stages prompt, sets resume target, and returns restart plan / executed status

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest local/tests/test_app_native_loop_tools.py -q`
Expected: FAIL on missing tool definitions or missing handlers

- [ ] **Step 3: Write minimal implementation**

Add the new tool definitions and handlers in `local/server/main.py`.
Keep side effects explicit:
- queue store write
- config resume target write
- optional app restart through existing controller

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest local/tests/test_app_native_loop_tools.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add local/server/main.py local/tests/test_app_native_loop_tools.py
git commit -m "add app-native loop queue and resume tools"
```

## Chunk 3: Session-Start Consume Seam

### Task 3: Define and test the consume-on-open contract

**Files:**
- Modify: `README.md`
- Optional create/modify: one narrow helper or integration note file if hook wiring is feasible
- Test: extend `local/tests/test_app_native_loop_tools.py` or add one focused test file

- [ ] **Step 1: Write the failing test or contract assertion**

Cover:
- consuming a queued prompt returns text only once
- repeated consume after first success returns empty / none

- [ ] **Step 2: Run test to verify it fails**

Run the focused pytest target
Expected: FAIL until consume-once path is explicit

- [ ] **Step 3: Write minimal implementation**

Either:
- expose a dedicated tool or helper for a future session-start hook to call, or
- if a hook integration point is directly available, wire it narrowly without broad app changes

- [ ] **Step 4: Run test to verify it passes**

Run focused pytest target
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "document app-native loop consume contract"
```

## Chunk 4: End-to-End Validation

### Task 4: Validate the first slice end to end

**Files:**
- Modify: `scripts/test.sh` only if needed to include new tests

- [ ] **Step 1: Run all relevant tests**

Run:
```bash
python3 -m pytest local/tests/test_prompt_queue_store.py local/tests/test_app_native_loop_tools.py -q
bash scripts/test.sh
```
Expected: all green

- [ ] **Step 2: Smoke-check queued prompt lifecycle manually**

Use the MCP-facing server entry or direct module invocation to confirm:
- queue prompt
- resume thread with queue
- consume once
- consume again returns empty

- [ ] **Step 3: Commit final validation updates if any**

```bash
git add scripts/test.sh README.md
 git commit -m "validate app-native loop transport"
```
