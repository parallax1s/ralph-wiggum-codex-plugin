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

    def test_submit_user_input_initializes_and_sends_follower_request(self) -> None:
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
                    "type": "response",
                    "requestId": "thread-follower-submit-user-input",
                    "resultType": "success",
                    "method": "thread-follower-submit-user-input",
                    "result": {"ok": True},
                },
            ]
        )

        with patch.object(socket, "socket", return_value=fake):
            client = LiveCodexIpcClient(socket_path=Path("/tmp/fake.sock"), timeout_seconds=0.1)
            result = client.submit_user_input(
                conversation_id="thread-1",
                message="continue",
            )

        self.assertEqual(result, {"ok": True})
        payloads = []
        for frame in fake.sent:
            size = struct.unpack("<I", frame[:4])[0]
            payloads.append(json.loads(frame[4 : 4 + size].decode("utf-8")))
        self.assertEqual(payloads[0]["method"], "initialize")
        self.assertEqual(payloads[1]["method"], "thread-follower-submit-user-input")
        self.assertEqual(payloads[1]["params"]["conversationId"], "thread-1")
        self.assertEqual(payloads[1]["params"]["message"], "continue")


if __name__ == "__main__":
    unittest.main()
