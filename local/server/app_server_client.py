from __future__ import annotations

import json
import subprocess
import time
from typing import Any


class CodexAppServerClient:
    def __init__(
        self,
        command: list[str] | None = None,
        timeout_seconds: float = 20.0,
        popen_factory: Any = None,
    ) -> None:
        self.command = command or ["codex", "app-server", "--listen", "stdio://"]
        self.timeout_seconds = timeout_seconds
        self.popen_factory = popen_factory or subprocess.Popen

    def send_prompt_to_thread(self, *, thread_id: str, message: str) -> dict[str, Any]:
        proc = self.popen_factory(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        try:
            self._send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "clientInfo": {"name": "ralph-wiggum-codex-plugin", "version": "0.1.0"},
                        "capabilities": {"optOutNotificationMethods": ["mcpServer/startupStatus/updated"]},
                    },
                },
            )
            self._recv_until_id(proc, 1)

            self._send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "thread/resume",
                    "params": {"threadId": thread_id},
                },
            )
            thread_response = self._recv_until_id(proc, 2)

            self._send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "turn/start",
                    "params": {
                        "threadId": thread_id,
                        "input": [{"type": "text", "text": message}],
                    },
                },
            )
            turn_response = self._recv_until_id(proc, 3)

            return {
                "thread": thread_response["result"]["thread"],
                "turn": turn_response["result"]["turn"],
            }
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=1)
            except Exception:
                proc.kill()

    def _send(self, proc: Any, payload: dict[str, Any]) -> None:
        if proc.stdin is None:
            raise RuntimeError("codex app-server stdin unavailable")
        proc.stdin.write(json.dumps(payload) + "\n")
        proc.stdin.flush()

    def _recv_until_id(self, proc: Any, request_id: int) -> dict[str, Any]:
        end = time.time() + self.timeout_seconds
        if proc.stdout is None:
            raise RuntimeError("codex app-server stdout unavailable")
        while time.time() < end:
            line = proc.stdout.readline()
            if not line:
                continue
            message = json.loads(line)
            if "error" in message:
                raise RuntimeError(f"codex app-server error: {message['error']}")
            if message.get("id") == request_id:
                return message
        raise TimeoutError(f"Timed out waiting for codex app-server response {request_id}")
