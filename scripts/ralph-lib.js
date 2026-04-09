"use strict";

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

function getRalphPaths(cwd) {
  const root = path.join(cwd, ".ralph");
  return {
    root,
    state: path.join(root, "ralph-loop.state.json"),
    history: path.join(root, "ralph-history.json"),
    context: path.join(root, "ralph-context.md"),
    tasks: path.join(root, "ralph-tasks.md"),
    logs: path.join(root, "logs"),
  };
}

function ensureRalphRoot(cwd) {
  const paths = getRalphPaths(cwd);
  fs.mkdirSync(paths.root, { recursive: true });
  fs.mkdirSync(paths.logs, { recursive: true });
  return paths;
}

function createInitialState(options) {
  const now = new Date().toISOString();
  return {
    version: 1,
    status: "running",
    pid: null,
    cwd: options.cwd,
    startedAt: now,
    updatedAt: now,
    iteration: 0,
    maxIterations: options.maxIterations,
    completionPromise: options.completionPromise,
    abortPromise: options.abortPromise || null,
    model: options.model || null,
    taskPrompt: options.taskPrompt,
    tasksMode: !!options.tasksMode,
    currentTask: null,
    stopRequested: false,
    lastExitCode: null,
    lastResult: null,
    lastError: null,
  };
}

function updateState(state, patch) {
  return {
    ...state,
    ...patch,
    updatedAt: new Date().toISOString(),
  };
}

function atomicWriteJson(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const tmpPath = `${filePath}.${crypto.randomBytes(4).toString("hex")}.tmp`;
  fs.writeFileSync(tmpPath, JSON.stringify(value, null, 2) + "\n");
  fs.renameSync(tmpPath, filePath);
}

function readJson(filePath, fallback) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return fallback;
  }
}

function appendHistory(historyPath, entry) {
  const history = readJson(historyPath, []);
  history.push(entry);
  atomicWriteJson(historyPath, history);
}

function readState(cwd) {
  return readJson(getRalphPaths(cwd).state, null);
}

function writeState(cwd, state) {
  atomicWriteJson(getRalphPaths(cwd).state, state);
}

function getIterationLogPath(cwd, iteration) {
  return path.join(getRalphPaths(cwd).logs, `iteration-${iteration}.log`);
}

function isPidAlive(pid) {
  if (!pid || typeof pid !== "number") {
    return false;
  }

  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

function buildIterationPrompt(state, contextText) {
  const parts = [
    state.taskPrompt,
    `Output <promise>${state.completionPromise}</promise> when complete.`,
  ];

  if (state.abortPromise) {
    parts.push(`Output <promise>${state.abortPromise}</promise> if the task is blocked by unmet preconditions.`);
  }

  if (contextText && contextText.trim() !== "") {
    parts.push(`Additional context:\n${contextText.trim()}`);
  }

  parts.push("Continue from the current repository state and previous changes.");
  return parts.join("\n\n");
}

function parseFlagArgs(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index++) {
    const arg = argv[index];
    if (!arg.startsWith("--")) {
      throw new Error(`Unknown argument: ${arg}`);
    }

    const key = arg.slice(2);
    const next = argv[index + 1];
    if (next === undefined || next.startsWith("--")) {
      parsed[key] = true;
      continue;
    }

    parsed[key] = next;
    index += 1;
  }
  return parsed;
}

module.exports = {
  appendHistory,
  atomicWriteJson,
  buildIterationPrompt,
  createInitialState,
  ensureRalphRoot,
  getIterationLogPath,
  getRalphPaths,
  isPidAlive,
  parseFlagArgs,
  readJson,
  readState,
  updateState,
  writeState,
};
