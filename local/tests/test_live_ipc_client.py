import io
import json
import socket
import struct
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class _FakeSocket:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self._buffer = b"".join(
            struct.pack("<I", len(data := json.dumps(resp).encode("utf-8"))) + data
            for resp in responses
        )
        self.sent = []

    def connect(self, path):
        self.path = path

    def settimeout(self, timeout):
        self.timeout = timeout

    def sendall(self, data):
        self.sent.append(data)

    def recv(self, size):
        if not self._buffer:
            return b""
        chunk = self._buffer[:size]
        self._buffer = self._buffer[size:]
        return chunk

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class LiveIpcClientTests(unittest.TestCase):
    def _imports(self):
        import sys

        sys.path.insert(0, str(ROOT))
        from server.live_ipc_client import LiveCodexIpcClient
        return LiveCodexIpcClient

    def test_start_turn_initializes_and_sends_follower_turn_request(self) -> None:
        LiveCodexIpcClient = self._imports()
        fake = _FakeSocket(
            [
                {
                    "type": "response",
                    "requestId": "init",
                    "resultType": "success",
                    "method": "initialize",
                    "result": {"clientId": "client-1"},
                },
                {
                    "type": "broadcast",
                    "method": "thread-stream-state-changed",
                    "sourceClientId": "owner-1",
                    "params": {
                        "conversationId": "thread-1",
                        "change": {
                            "type": "snapshot",
                            "conversationState": {
                                "id": "thread-1",
                                "turns": [],
                            },
                        },
                    },
                },
                {
                    "type": "response",
                    "requestId": "thread-follower-start-turn:req-1",
                    "resultType": "success",
                    "method": "thread-follower-start-turn",
                    "result": {"turn": {"id": "turn-1", "status": "inProgress"}},
                },
            ]
        )

        with patch.object(socket, "socket", return_value=fake):
            client = LiveCodexIpcClient(socket_path=Path("/tmp/fake.sock"), timeout_seconds=0.1)
            with patch("server.live_ipc_client.uuid.uuid4", return_value="req-1"):
                result = client.start_turn(
                conversation_id="thread-1",
                message="continue",
                )

        self.assertEqual(result, {"turn": {"id": "turn-1", "status": "inProgress"}})
        payloads = []
        for frame in fake.sent:
            size = struct.unpack("<I", frame[:4])[0]
            payloads.append(json.loads(frame[4 : 4 + size].decode("utf-8")))
        self.assertEqual(payloads[0]["method"], "initialize")
        self.assertEqual(payloads[1]["method"], "thread-follower-start-turn")
        self.assertEqual(payloads[1]["targetClientId"], "owner-1")
        self.assertEqual(payloads[1]["params"]["conversationId"], "thread-1")
        self.assertEqual(
            payloads[1]["params"]["turnStartParams"]["input"],
            [{"type": "text", "text": "continue"}],
        )

    def test_start_turn_rejects_when_thread_already_in_progress(self) -> None:
        LiveCodexIpcClient = self._imports()
        fake = _FakeSocket(
            [
                {
                    "type": "response",
                    "requestId": "init",
                    "resultType": "success",
                    "method": "initialize",
                    "result": {"clientId": "client-1"},
                },
                {
                    "type": "broadcast",
                    "method": "thread-stream-state-changed",
                    "sourceClientId": "owner-1",
                    "params": {
                        "conversationId": "thread-1",
                        "change": {
                            "type": "snapshot",
                            "conversationState": {
                                "id": "thread-1",
                                "turns": [
                                    {"turnId": "turn-in-flight", "status": "inProgress"},
                                ],
                            },
                        },
                    },
                },
            ]
        )

        with patch.object(socket, "socket", return_value=fake):
            client = LiveCodexIpcClient(socket_path=Path("/tmp/fake.sock"), timeout_seconds=0.1)
            with self.assertRaisesRegex(RuntimeError, "in-progress"):
                client.start_turn(conversation_id="thread-1", message="continue")

    def test_interrupt_conversation_targets_owner(self) -> None:
        LiveCodexIpcClient = self._imports()
        fake = _FakeSocket(
            [
                {
                    "type": "response",
                    "requestId": "init",
                    "resultType": "success",
                    "method": "initialize",
                    "result": {"clientId": "client-1"},
                },
                {
                    "type": "broadcast",
                    "method": "thread-stream-state-changed",
                    "sourceClientId": "owner-1",
                    "params": {
                        "conversationId": "thread-1",
                        "change": {
                            "type": "snapshot",
                            "conversationState": {
                                "id": "thread-1",
                                "turns": [{"turnId": "turn-in-flight", "status": "inProgress"}],
                            },
                        },
                    },
                },
                {
                    "type": "response",
                    "requestId": "thread-follower-interrupt-turn:req-2",
                    "resultType": "success",
                    "method": "thread-follower-interrupt-turn",
                    "result": {"ok": True},
                },
            ]
        )

        with patch.object(socket, "socket", return_value=fake):
            client = LiveCodexIpcClient(socket_path=Path("/tmp/fake.sock"), timeout_seconds=0.1)
            with patch("server.live_ipc_client.uuid.uuid4", return_value="req-2"):
                result = client.interrupt_conversation(conversation_id="thread-1")

        self.assertEqual(result, {"ok": True})
        payloads = []
        for frame in fake.sent:
            size = struct.unpack("<I", frame[:4])[0]
            payloads.append(json.loads(frame[4 : 4 + size].decode("utf-8")))
        self.assertEqual(payloads[1]["method"], "thread-follower-interrupt-turn")
        self.assertEqual(payloads[1]["targetClientId"], "owner-1")

    def test_wait_for_turn_terminal_returns_completed_turn(self) -> None:
        LiveCodexIpcClient = self._imports()
        fake = _FakeSocket(
            [
                {
                    "type": "response",
                    "requestId": "init",
                    "resultType": "success",
                    "method": "initialize",
                    "result": {"clientId": "client-1"},
                },
                {
                    "type": "broadcast",
                    "method": "thread-stream-state-changed",
                    "sourceClientId": "owner-1",
                    "params": {
                        "conversationId": "thread-1",
                        "change": {
                            "type": "snapshot",
                            "conversationState": {
                                "id": "thread-1",
                                "turns": [{"turnId": "turn-1", "status": "inProgress"}],
                            },
                        },
                    },
                },
                {
                    "type": "broadcast",
                    "method": "thread-stream-state-changed",
                    "sourceClientId": "owner-1",
                    "params": {
                        "conversationId": "thread-1",
                        "change": {
                            "type": "snapshot",
                            "conversationState": {
                                "id": "thread-1",
                                "turns": [
                                    {
                                        "turnId": "turn-1",
                                        "status": "completed",
                                        "items": [{"type": "agentMessage", "text": "done"}],
                                    }
                                ],
                            },
                        },
                    },
                },
            ]
        )

        with patch.object(socket, "socket", return_value=fake):
            client = LiveCodexIpcClient(socket_path=Path("/tmp/fake.sock"), timeout_seconds=0.1)
            result = client.wait_for_turn_terminal(conversation_id="thread-1", turn_id="turn-1")

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["items"][0]["text"], "done")

    def test_wait_for_turn_settled_returns_when_idle_after_terminal_turn(self) -> None:
        LiveCodexIpcClient = self._imports()
        fake = _FakeSocket(
            [
                {
                    "type": "response",
                    "requestId": "init",
                    "resultType": "success",
                    "method": "initialize",
                    "result": {"clientId": "client-1"},
                },
                {
                    "type": "broadcast",
                    "method": "thread-stream-state-changed",
                    "sourceClientId": "owner-1",
                    "params": {
                        "conversationId": "thread-1",
                        "change": {
                            "type": "snapshot",
                            "conversationState": {
                                "id": "thread-1",
                                "turns": [
                                    {"turnId": "turn-1", "status": "completed", "items": [{"type": "agentMessage", "text": "done"}]},
                                ],
                                "requests": [],
                            },
                        },
                    },
                },
            ]
        )

        with patch.object(socket, "socket", return_value=fake):
            client = LiveCodexIpcClient(socket_path=Path("/tmp/fake.sock"), timeout_seconds=0.1)
            result = client.wait_for_turn_settled(conversation_id="thread-1", turn_id="turn-1", quiet_seconds=0)

        self.assertEqual(result["outcome"], "settled")
        self.assertEqual(result["turn"]["status"], "completed")

    def test_wait_for_turn_settled_reports_superseded_when_newer_turn_appears(self) -> None:
        LiveCodexIpcClient = self._imports()
        fake = _FakeSocket(
            [
                {
                    "type": "response",
                    "requestId": "init",
                    "resultType": "success",
                    "method": "initialize",
                    "result": {"clientId": "client-1"},
                },
                {
                    "type": "broadcast",
                    "method": "thread-stream-state-changed",
                    "sourceClientId": "owner-1",
                    "params": {
                        "conversationId": "thread-1",
                        "change": {
                            "type": "snapshot",
                            "conversationState": {
                                "id": "thread-1",
                                "turns": [
                                    {"turnId": "turn-1", "status": "completed"},
                                    {"turnId": "turn-2", "status": "inProgress"},
                                ],
                                "requests": [],
                            },
                        },
                    },
                },
            ]
        )

        with patch.object(socket, "socket", return_value=fake):
            client = LiveCodexIpcClient(socket_path=Path("/tmp/fake.sock"), timeout_seconds=0.1)
            result = client.wait_for_turn_settled(conversation_id="thread-1", turn_id="turn-1", quiet_seconds=0)

        self.assertEqual(result["outcome"], "superseded")
        self.assertEqual(result["supersedingTurn"]["turnId"], "turn-2")


if __name__ == "__main__":
    unittest.main()
