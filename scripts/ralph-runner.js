#!/usr/bin/env node
"use strict";

const fs = require("fs");
const { spawnSync } = require("child_process");
const {
  appendHistory,
  buildIterationPrompt,
  getIterationLogPath,
  getRalphPaths,
  readState,
  updateState,
  writeState,
} = require("./ralph-lib");

function getCodexCommand(state) {
  return process.env.RALPH_CODEX_BINARY || "codex";
}

function getCodexArgs(state, prompt) {
  const args = ["exec"];
  if (state.model) {
    args.push("--model", state.model);
  }
  args.push(prompt);
  return args;
}

function detectResult(output, state) {
  const completionMarker = `<promise>${state.completionPromise}</promise>`;
  if (output.includes(completionMarker)) {
    return "completed";
  }

  if (state.abortPromise) {
    const abortMarker = `<promise>${state.abortPromise}</promise>`;
    if (output.includes(abortMarker)) {
      return "aborted";
    }
  }

  return null;
}

function runIteration(state) {
  const paths = getRalphPaths(state.cwd);
  const contextText = fs.existsSync(paths.context) ? fs.readFileSync(paths.context, "utf8") : "";
  const prompt = buildIterationPrompt(state, contextText);
  const command = getCodexCommand(state);
  const args = getCodexArgs(state, prompt);
  const iteration = state.iteration + 1;
  const logPath = getIterationLogPath(state.cwd, iteration);
  const startedAt = new Date().toISOString();

  const result = spawnSync(command, args, {
    cwd: state.cwd,
    env: process.env,
    encoding: "utf8",
  });

  const stdout = result.stdout || "";
  const stderr = result.stderr || "";
  fs.mkdirSync(paths.logs, { recursive: true });
  fs.writeFileSync(logPath, `${stdout}${stderr}`, "utf8");

  const combined = `${stdout}${stderr}`;
  const outcome = detectResult(combined, state);
  appendHistory(paths.history, {
    iteration,
    startedAt,
    endedAt: new Date().toISOString(),
    exitCode: result.status,
    completionDetected: outcome === "completed",
    abortDetected: outcome === "aborted",
    logPath,
  });

  let nextState = updateState(state, {
    iteration,
    lastExitCode: result.status,
    lastError: result.error ? String(result.error.message || result.error) : null,
  });

  if (outcome === "completed") {
    nextState = updateState(nextState, { status: "completed", lastResult: "completed" });
  } else if (outcome === "aborted") {
    nextState = updateState(nextState, { status: "aborted", lastResult: "aborted" });
  } else if (iteration >= state.maxIterations) {
    nextState = updateState(nextState, { status: "failed", lastResult: "max-iterations-reached" });
  }

  writeState(state.cwd, nextState);
  return nextState;
}

function main() {
  let state = readState(process.cwd());
  if (!state) {
    throw new Error("Missing Ralph state");
  }

  while (state.status === "running" && state.iteration < state.maxIterations) {
    state = runIteration(state);
  }
}

try {
  main();
} catch (error) {
  const state = readState(process.cwd());
  if (state) {
    writeState(process.cwd(), updateState(state, {
      status: "failed",
      lastResult: "failed",
      lastError: error.message || String(error),
    }));
  }
  process.exit(1);
}
