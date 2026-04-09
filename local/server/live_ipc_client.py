from __future__ import annotations

import json
import os
import socket
import struct
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any


def _default_socket_path() -> Path:
    tmp_root = Path(tempfile.gettempdir()) / "codex-ipc"
    uid = os.getuid() if hasattr(os, "getuid") else None
    return tmp_root / (f"ipc-{uid}.sock" if uid else "ipc.sock")


class LiveCodexIpcClient:
    def __init__(self, socket_path: Path | None = None, timeout_seconds: float = 6.0) -> None:
        self.socket_path = Path(socket_path or _default_socket_path())
        self.timeout_seconds = timeout_seconds

    def submit_user_input(self, *, conversation_id: str, message: str) -> dict[str, Any]:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(str(self.socket_path))
            client_id = self._initialize(sock)
            response = self._request(
                sock,
                client_id=client_id,
                method="thread-follower-submit-user-input",
                params={"conversationId": conversation_id, "message": message},
                request_id="thread-follower-submit-user-input",
            )
            if response.get("resultType") != "success":
                raise RuntimeError(response.get("error") or "live-ipc-request-failed")
            return response.get("result") or {}

    def _initialize(self, sock: socket.socket) -> str:
        response = self._request(
            sock,
            client_id="initializing-client",
            method="initialize",
            params={"clientType": "ralph-probe"},
            request_id="init",
            version=1,
        )
        return str(response["result"]["clientId"])

    def _request(
        self,
        sock: socket.socket,
        *,
        client_id: str,
        method: str,
        params: dict[str, Any],
        request_id: str,
        version: int = 1,
    ) -> dict[str, Any]:
        payload = {
            "type": "request",
            "requestId": request_id,
            "sourceClientId": client_id,
            "version": version,
            "method": method,
            "params": params,
        }
        sock.sendall(self._frame(payload))
        end = time.time() + self.timeout_seconds
        while time.time() < end:
            try:
                message = self._recv_one(sock, min(2.0, max(0.1, end - time.time())))
            except TimeoutError:
                continue
            if message.get("type") == "response" and message.get("requestId") == request_id:
                return message
        raise TimeoutError(f"Timed out waiting for live IPC response: {method}")

    def _recv_one(self, sock: socket.socket, timeout: float) -> dict[str, Any]:
        sock.settimeout(timeout)
        header = sock.recv(4)
        if not header:
            raise RuntimeError("live IPC socket closed")
        frame_length = struct.unpack("<I", header)[0]
        body = b""
        while len(body) < frame_length:
          chunk = sock.recv(frame_length - len(body))
          if not chunk:
              raise RuntimeError("live IPC socket closed during frame read")
          body += chunk
        return json.loads(body.decode("utf-8"))

    @staticmethod
    def _frame(payload: dict[str, Any]) -> bytes:
        data = json.dumps(payload).encode("utf-8")
        return struct.pack("<I", len(data)) + data
