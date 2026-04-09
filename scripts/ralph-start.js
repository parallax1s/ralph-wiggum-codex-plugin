#!/usr/bin/env node
"use strict";

const path = require("path");
const { spawn } = require("child_process");
const {
  createInitialState,
  ensureRalphRoot,
  isPidAlive,
  readState,
  updateState,
  writeState,
} = require("./ralph-lib");

function parseArgs(argv) {
  const parsed = {
    prompt: "",
    maxIterations: 0,
    completionPromise: "COMPLETE",
    abortPromise: null,
    model: null,
    tasksMode: false,
    force: false,
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
      case "--abort-promise":
        parsed.abortPromise = argv[++index] || "";
        break;
      case "--model":
        parsed.model = argv[++index] || "";
        break;
      case "--tasks":
        parsed.tasksMode = true;
        break;
      case "--force":
        parsed.force = true;
        break;
      default:
        throw new Error(`Unknown argument: ${arg}`);
    }
  }

  if (!parsed.prompt.trim()) {
    throw new Error("Missing required argument: --prompt");
  }
  if (!Number.isInteger(parsed.maxIterations) || parsed.maxIterations < 1) {
    throw new Error("Missing or invalid argument: --max-iterations");
  }

  return parsed;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const cwd = process.cwd();
  ensureRalphRoot(cwd);

  const existing = readState(cwd);
  if (!args.force && existing && existing.status === "running" && isPidAlive(existing.pid)) {
    throw new Error("Ralph loop already running in this repository");
  }

  let state = createInitialState({
    cwd,
    maxIterations: args.maxIterations,
    completionPromise: args.completionPromise,
    abortPromise: args.abortPromise,
    model: args.model,
    taskPrompt: args.prompt,
    tasksMode: args.tasksMode,
  });
  writeState(cwd, state);

  const runnerPath = path.join(__dirname, "ralph-runner.js");
  const child = spawn(process.execPath, [runnerPath], {
    cwd,
    detached: true,
    stdio: "ignore",
    env: process.env,
  });
  child.unref();

  state = updateState(state, { pid: child.pid });
  writeState(cwd, state);
  console.log(JSON.stringify({ started: true, pid: child.pid, cwd }));
}

try {
  main();
} catch (error) {
  console.error(error.message || String(error));
  process.exit(1);
}
