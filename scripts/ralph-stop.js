#!/usr/bin/env node
"use strict";

const { isPidAlive, readState, updateState, writeState } = require("./ralph-lib");

try {
  const cwd = process.cwd();
  const state = readState(cwd);
  if (!state) {
    throw new Error("No Ralph state found in this repository");
  }

  const nextState = updateState(state, {
    status: "stopped",
    stopRequested: true,
    lastResult: "stopped",
  });
  writeState(cwd, nextState);

  if (isPidAlive(state.pid)) {
    process.kill(state.pid, "SIGTERM");
  }

  console.log(`Stopped Ralph loop for ${cwd}`);
} catch (error) {
  console.error(error.message || String(error));
  process.exit(1);
}
