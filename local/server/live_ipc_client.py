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

    def start_turn(self, *, conversation_id: str, message: str) -> dict[str, Any]:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(str(self.socket_path))
            client_id = self._initialize(sock)
            owner_client_id, conversation_state = self._await_conversation_state(
                sock,
                conversation_id=conversation_id,
            )
            in_progress_turns = [
                turn
                for turn in conversation_state.get("turns", [])
                if turn.get("status") == "inProgress"
            ]
            if in_progress_turns:
                raise RuntimeError(
                    "conversation already has in-progress turn(s): "
                    + ", ".join(str(turn.get("turnId")) for turn in in_progress_turns if turn.get("turnId"))
                )
            response = self._request(
                sock,
                client_id=client_id,
                method="thread-follower-start-turn",
                params={
                    "conversationId": conversation_id,
                    "turnStartParams": {
                        "input": [{"type": "text", "text": message}],
                    },
                },
                request_id=f"thread-follower-start-turn:{uuid.uuid4()}",
                target_client_id=owner_client_id,
            )
            if response.get("resultType") != "success":
                raise RuntimeError(response.get("error") or "live-ipc-request-failed")
            return response.get("result") or {}

    def interrupt_conversation(self, *, conversation_id: str) -> dict[str, Any]:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(str(self.socket_path))
            client_id = self._initialize(sock)
            owner_client_id, _ = self._await_conversation_state(
                sock,
                conversation_id=conversation_id,
            )
            response = self._request(
                sock,
                client_id=client_id,
                method="thread-follower-interrupt-turn",
                params={"conversationId": conversation_id},
                request_id=f"thread-follower-interrupt-turn:{uuid.uuid4()}",
                target_client_id=owner_client_id,
            )
            if response.get("resultType") != "success":
                raise RuntimeError(response.get("error") or "live-ipc-request-failed")
            return response.get("result") or {}

    def wait_for_turn_terminal(self, *, conversation_id: str, turn_id: str) -> dict[str, Any]:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(str(self.socket_path))
            self._initialize(sock)
            end = time.time() + self.timeout_seconds
            while time.time() < end:
                owner_client_id, conversation_state = self._await_conversation_state(
                    sock,
                    conversation_id=conversation_id,
                )
                del owner_client_id
                for turn in conversation_state.get("turns", []):
                    if turn.get("turnId") != turn_id:
                        continue
                    if turn.get("status") != "inProgress":
                        return turn
            raise TimeoutError(f"Timed out waiting for turn to become terminal: {turn_id}")

    def wait_for_turn_settled(
        self,
        *,
        conversation_id: str,
        turn_id: str,
        quiet_seconds: float = 2.0,
    ) -> dict[str, Any]:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(str(self.socket_path))
            self._initialize(sock)
            end = time.time() + self.timeout_seconds
            ready_at: float | None = None
            terminal_turn: dict[str, Any] | None = None

            while time.time() < end:
                remaining = min(2.0, max(0.05, end - time.time()))
                try:
                    owner_client_id, conversation_state = self._await_conversation_state(
                        sock,
                        conversation_id=conversation_id,
                    )
                    del owner_client_id
                except TimeoutError:
                    if ready_at is not None and time.time() >= ready_at:
                        return {"outcome": "settled", "turn": terminal_turn}
                    continue

                turns = conversation_state.get("turns", [])
                target_index = next((i for i, turn in enumerate(turns) if turn.get("turnId") == turn_id), -1)
                if target_index < 0:
                    raise RuntimeError(f"turn not found in conversation state: {turn_id}")

                target_turn = turns[target_index]
                newer_turns = turns[target_index + 1 :]
                if newer_turns:
                    return {
                        "outcome": "superseded",
                        "turn": target_turn,
                        "supersedingTurn": newer_turns[-1],
                    }

                if target_turn.get("status") == "inProgress":
                    ready_at = None
                    terminal_turn = None
                    continue

                in_progress_turns = [turn for turn in turns if turn.get("status") == "inProgress"]
                requests = conversation_state.get("requests", [])
                if in_progress_turns or requests:
                    ready_at = None
                    terminal_turn = target_turn
                    continue

                terminal_turn = target_turn
                if quiet_seconds <= 0:
                    return {"outcome": "settled", "turn": terminal_turn}
                ready_at = time.time() + quiet_seconds
                while time.time() < min(end, ready_at):
                    try:
                        owner_client_id, conversation_state = self._await_conversation_state(
                            sock,
                            conversation_id=conversation_id,
                        )
                        del owner_client_id
                    except TimeoutError:
                        continue
                    turns = conversation_state.get("turns", [])
                    target_index = next((i for i, turn in enumerate(turns) if turn.get("turnId") == turn_id), -1)
                    if target_index < 0:
                        raise RuntimeError(f"turn not found in conversation state: {turn_id}")
                    target_turn = turns[target_index]
                    newer_turns = turns[target_index + 1 :]
                    if newer_turns:
                        return {
                            "outcome": "superseded",
                            "turn": target_turn,
                            "supersedingTurn": newer_turns[-1],
                        }
                    if target_turn.get("status") == "inProgress" or conversation_state.get("requests") or any(
                        turn.get("status") == "inProgress" for turn in turns
                    ):
                        ready_at = None
                        terminal_turn = target_turn
                        break
                else:
                    return {"outcome": "settled", "turn": terminal_turn}

            raise TimeoutError(f"Timed out waiting for turn to settle: {turn_id}")

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
        target_client_id: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "type": "request",
            "requestId": request_id,
            "sourceClientId": client_id,
            "version": version,
            "method": method,
            "params": params,
        }
        if target_client_id:
            payload["targetClientId"] = target_client_id
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

    def _await_conversation_state(self, sock: socket.socket, *, conversation_id: str) -> tuple[str, dict[str, Any]]:
        end = time.time() + self.timeout_seconds
        while time.time() < end:
            try:
                message = self._recv_one(sock, min(2.0, max(0.1, end - time.time())))
            except TimeoutError:
                continue
            if (
                message.get("type") == "broadcast"
                and message.get("method") == "thread-stream-state-changed"
                and message.get("params", {}).get("conversationId") == conversation_id
            ):
                change = message.get("params", {}).get("change", {})
                conversation_state = change.get("conversationState")
                if isinstance(conversation_state, dict):
                    owner_client_id = str(message.get("sourceClientId") or "")
                    if not owner_client_id:
                        raise RuntimeError("missing source client id for conversation state broadcast")
                    return owner_client_id, conversation_state
        raise TimeoutError(f"Timed out waiting for conversation state: {conversation_id}")

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
