#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

function codexHome() {
  return process.env.CODEX_HOME || path.join(os.homedir(), ".codex");
}

function configPath() {
  return process.env.CODEX_THREAD_RESUMER_CONFIG || path.join(codexHome(), "config.toml");
}

function queuePath() {
  return process.env.CODEX_THREAD_RESUMER_PROMPT_QUEUE || path.join(codexHome(), "thread-resumer-prompt-queue.json");
}

function upstreamHookPath() {
  return process.env.RALPH_UPSTREAM_SESSION_START || path.join(codexHome(), "superpowers", "hooks", "session-start");
}

function readExperimentalResume() {
  const cfg = configPath();
  if (!fs.existsSync(cfg)) {
    return null;
  }
  const text = fs.readFileSync(cfg, "utf8");
  const match = text.match(/^experimental_resume\s*=\s*"([^"]+)"\s*$/m);
  return match ? match[1] : null;
}

function consumeQueuedPrompt(rolloutPath) {
  const qp = queuePath();
  if (!rolloutPath || !fs.existsSync(qp)) {
    return null;
  }
  const payload = JSON.parse(fs.readFileSync(qp, "utf8"));
  for (const [threadId, record] of Object.entries(payload)) {
    if (record && typeof record === "object" && record.rollout_path === rolloutPath) {
      delete payload[threadId];
      fs.writeFileSync(qp, JSON.stringify(payload, null, 2), "utf8");
      return record;
    }
  }
  return null;
}

function runUpstreamHook() {
  const hook = upstreamHookPath();
  if (!fs.existsSync(hook)) {
    return {};
  }
  const result = spawnSync(hook, {
    cwd: process.cwd(),
    env: process.env,
    encoding: "utf8",
  });
  const stdout = result.stdout || "";
  if (!stdout.trim()) {
    return {};
  }
  return JSON.parse(stdout);
}

function mergeContext(base, extra) {
  if (!extra) {
    return base;
  }
  if (base.hookSpecificOutput && typeof base.hookSpecificOutput.additionalContext === "string") {
    base.hookSpecificOutput.additionalContext += `\n\n${extra}`;
    return base;
  }
  if (typeof base.additional_context === "string") {
    base.additional_context += `\n\n${extra}`;
    return base;
  }
  if (process.env.CLAUDE_PLUGIN_ROOT) {
    return {
      hookSpecificOutput: {
        hookEventName: "SessionStart",
        additionalContext: extra,
      },
    };
  }
  return {
    additional_context: extra,
  };
}

function main() {
  const upstream = runUpstreamHook();
  const rolloutPath = readExperimentalResume();
  const queued = consumeQueuedPrompt(rolloutPath);
  const extra = queued
    ? `<important>Queued loop prompt for this resumed thread: ${queued.message}</important>`
    : null;
  process.stdout.write(`${JSON.stringify(mergeContext(upstream, extra), null, 2)}\n`);
}

main();
