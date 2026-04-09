#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local"))

from server.live_ipc_client import LiveCodexIpcClient  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--max-iterations", default="5")
    parser.add_argument("--iteration-timeout-ms", default="300000")
    parser.add_argument("--completion-promise", default="COMPLETE")
    parser.add_argument("--quiet-seconds", type=float, default=2.0)
    return parser.parse_args()


def _await_launchable_settle(client: LiveCodexIpcClient, *, thread_id: str, quiet_seconds: float) -> dict:
    while True:
        settled = client.wait_for_latest_turn_settled(
            conversation_id=thread_id,
            quiet_seconds=quiet_seconds,
        )
        if settled.get("outcome") == "superseded":
            superseding_turn = settled.get("supersedingTurn") or {}
            superseding_id = superseding_turn.get("turnId")
            if superseding_id:
                print(
                    f"[ralph-arm-visible-thread] superseded by newer turn {superseding_id}; continuing to watch",
                    file=sys.stderr,
                )
            continue
        return settled


def main() -> int:
    args = _parse_args()
    timeout_seconds = max(1.0, int(args.iteration_timeout_ms) / 1000.0)
    client = LiveCodexIpcClient(timeout_seconds=timeout_seconds)
    settled = _await_launchable_settle(
        client,
        thread_id=args.thread_id,
        quiet_seconds=args.quiet_seconds,
    )

    command = [
        "node",
        str(ROOT / "scripts" / "ralph-start.js"),
        "--transport",
        "visible-thread",
        "--thread-id",
        args.thread_id,
        "--prompt",
        args.prompt,
        "--max-iterations",
        str(args.max_iterations),
        "--iteration-timeout-ms",
        str(args.iteration_timeout_ms),
        "--completion-promise",
        args.completion_promise,
    ]
    completed = subprocess.run(command, cwd=str(Path.cwd()))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
