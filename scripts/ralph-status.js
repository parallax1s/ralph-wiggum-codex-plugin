#!/usr/bin/env node
"use strict";

const { readState } = require("./ralph-lib");

try {
  const state = readState(process.cwd());
  if (!state) {
    throw new Error("No Ralph state found in this repository");
  }

  console.log(`Status: ${state.status}`);
  console.log(`Iteration: ${state.iteration}/${state.maxIterations}`);
  if (state.pid) {
    console.log(`PID: ${state.pid}`);
  }
  if (state.lastResult) {
    console.log(`Last result: ${state.lastResult}`);
  }
  if (state.lastError) {
    console.log(`Last error: ${state.lastError}`);
  }
} catch (error) {
  console.error(error.message || String(error));
  process.exit(1);
}
