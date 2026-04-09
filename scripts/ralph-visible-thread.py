#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local"))

from server.live_ipc_client import LiveCodexIpcClient  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--message", required=True)
    parser.add_argument("--timeout-ms", type=int, required=True)
    return parser.parse_args()


def _emit_turn_output(turn: dict) -> None:
    for item in turn.get("items", []):
        if item.get("type") == "agentMessage":
            text = item.get("text")
            if text:
                print(text)


def _extract_turn_id(result: dict) -> str | None:
    turn = result.get("turn") if isinstance(result, dict) else None
    if isinstance(turn, dict):
        return turn.get("id") or turn.get("turnId")
    if isinstance(result, dict):
        return result.get("id") or result.get("turnId")
    return None


def _extract_busy_turn_id(error: RuntimeError) -> str | None:
    match = re.search(r"in-progress turn\(s\):\s*(\S+)", str(error))
    return match.group(1) if match else None


def _start_turn_with_retry(client: LiveCodexIpcClient, *, thread_id: str, message: str, timeout_seconds: float) -> dict:
    deadline = time.time() + timeout_seconds
    while True:
        try:
            return client.start_turn(conversation_id=thread_id, message=message)
        except RuntimeError as error:
            if "conversation already has in-progress turn(s)" not in str(error):
                raise
            if time.time() >= deadline:
                raise
            busy_turn_id = _extract_busy_turn_id(error)
            settled = client.wait_for_latest_turn_settled(conversation_id=thread_id, quiet_seconds=0)
            settled_turn = settled.get("turn") if isinstance(settled, dict) else None
            settled_turn_id = None
            if isinstance(settled_turn, dict):
                settled_turn_id = settled_turn.get("turnId") or settled_turn.get("id")
            if busy_turn_id and settled_turn_id and settled_turn_id != busy_turn_id:
                raise RuntimeError(
                    f"visible-thread start superseded while waiting to retry: {busy_turn_id} -> {settled_turn_id}"
                )


def main() -> int:
    args = _parse_args()
    timeout_seconds = max(1.0, args.timeout_ms / 1000.0)
    client = LiveCodexIpcClient(timeout_seconds=timeout_seconds)
    result = _start_turn_with_retry(
        client,
        thread_id=args.thread_id,
        message=args.message,
        timeout_seconds=timeout_seconds,
    )
    turn_id = _extract_turn_id(result)
    if not turn_id:
      print("missing turn id from visible-thread start", file=sys.stderr)
      return 1
    print(f"[ralph-visible-thread] started turn {turn_id}", file=sys.stderr)
    settled = client.wait_for_turn_settled(conversation_id=args.thread_id, turn_id=str(turn_id), quiet_seconds=2.0)
    if settled.get("outcome") == "superseded":
        superseding_turn = settled.get("supersedingTurn") or {}
        superseding_id = superseding_turn.get("turnId")
        if superseding_id:
            print(f"[ralph-visible-thread] superseded by newer turn {superseding_id}", file=sys.stderr)
        print("<promise>COMPLETE</promise>")
        return 0
    terminal_turn = settled["turn"]
    _emit_turn_output(terminal_turn)
    if terminal_turn.get("status") == "completed":
        return 0
    error = terminal_turn.get("error") or {}
    message = error.get("message") if isinstance(error, dict) else str(error)
    if message:
        print(message, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
