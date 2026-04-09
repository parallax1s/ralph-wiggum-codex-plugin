#!/usr/bin/env node
"use strict";

const path = require("path");
const { spawn } = require("child_process");
const {
  createInitialState,
  ensureRalphCodexHome,
  ensureRalphRoot,
  isPidAlive,
  readState,
  updateState,
  writeState,
} = require("./ralph-lib");

function parseArgs(argv) {
  const parsed = {
    prompt: "",
    maxIterations: 256,
    iterationTimeoutMs: 60000,
    completionPromise: "COMPLETE",
    abortPromise: null,
    model: null,
    transport: "codex-exec",
    threadId: null,
    tasksMode: false,
    force: false,
    background: false,
  };

  for (let index = 0; index < argv.length; index++) {
    const arg = argv[index];
    switch (arg) {
      case "--prompt":
        parsed.prompt = argv[++index] || "";
        break;
      case "--max-iterations":
        parsed.maxIterations = Number(argv[++index] || "0");
        break;
      case "--completion-promise":
        parsed.completionPromise = argv[++index] || "COMPLETE";
        break;
      case "--iteration-timeout-ms":
        parsed.iterationTimeoutMs = Number(argv[++index] || "0");
        break;
      case "--abort-promise":
        parsed.abortPromise = argv[++index] || "";
        break;
      case "--model":
        parsed.model = argv[++index] || "";
        break;
      case "--transport":
        parsed.transport = argv[++index] || "";
        break;
      case "--thread-id":
        parsed.threadId = argv[++index] || "";
        break;
      case "--tasks":
        parsed.tasksMode = true;
        break;
      case "--force":
        parsed.force = true;
        break;
      case "--background":
        parsed.background = true;
        break;
      case "--foreground":
        parsed.background = false;
        break;
      default:
        throw new Error(`Unknown argument: ${arg}`);
    }
  }

  if (!parsed.prompt.trim()) {
    throw new Error("Missing required argument: --prompt");
  }
  if (!Number.isInteger(parsed.maxIterations) || parsed.maxIterations < 1) {
    throw new Error("Invalid argument: --max-iterations");
  }
  if (!Number.isInteger(parsed.iterationTimeoutMs) || parsed.iterationTimeoutMs < 1) {
    throw new Error("Missing or invalid argument: --iteration-timeout-ms");
  }
  if (!["codex-exec", "visible-thread"].includes(parsed.transport)) {
    throw new Error("Missing or invalid argument: --transport");
  }
  if (parsed.transport === "visible-thread" && !parsed.threadId?.trim()) {
    throw new Error("Missing required argument: --thread-id");
  }

  return parsed;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const cwd = process.cwd();
  ensureRalphRoot(cwd);
  const codexHome = ensureRalphCodexHome(process.env);

  const existing = readState(cwd);
  if (!args.force && existing && existing.status === "running" && isPidAlive(existing.pid)) {
    throw new Error("Ralph loop already running in this repository");
  }

  let state = createInitialState({
    cwd,
    maxIterations: args.maxIterations,
    iterationTimeoutMs: args.iterationTimeoutMs,
    completionPromise: args.completionPromise,
    abortPromise: args.abortPromise,
    model: args.model,
    transport: args.transport,
    threadId: args.threadId,
    taskPrompt: args.prompt,
    tasksMode: args.tasksMode,
  });
  writeState(cwd, state);

  const runnerPath = path.join(__dirname, "ralph-runner.js");

  if (args.background) {
    const child = spawn(process.execPath, [runnerPath], {
      cwd,
      detached: true,
      stdio: "ignore",
      env: { ...process.env, CODEX_HOME: codexHome },
    });
    child.unref();

    state = updateState(state, { pid: child.pid });
    writeState(cwd, state);
    console.log(JSON.stringify({ started: true, mode: "background", pid: child.pid, cwd }));
    return;
  }

  const result = spawn(process.execPath, [runnerPath], {
    cwd,
    stdio: "inherit",
    env: { ...process.env, CODEX_HOME: codexHome },
  });

  result.on("exit", (code) => {
    process.exit(code ?? 0);
  });
}

try {
  main();
} catch (error) {
  console.error(error.message || String(error));
  process.exit(1);
}
