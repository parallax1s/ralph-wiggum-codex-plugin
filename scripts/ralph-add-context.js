#!/usr/bin/env node
"use strict";

const fs = require("fs");
const { ensureRalphRoot, getRalphPaths, parseFlagArgs } = require("./ralph-lib");

try {
  const args = parseFlagArgs(process.argv.slice(2));
  const message = String(args.message || "").trim();
  if (!message) {
    throw new Error("Missing required argument: --message");
  }

  const cwd = process.cwd();
  ensureRalphRoot(cwd);
  const contextPath = getRalphPaths(cwd).context;
  const entry = `## ${new Date().toISOString()}\n${message}\n`;
  fs.appendFileSync(contextPath, (fs.existsSync(contextPath) ? "\n" : "") + entry, "utf8");
  console.log(`Appended context to ${contextPath}`);
} catch (error) {
  console.error(error.message || String(error));
  process.exit(1);
}
