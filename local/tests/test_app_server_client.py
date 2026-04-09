import io
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class _FakeProcess:
    def __init__(self, lines: list[dict[str, object]]) -> None:
        self.stdin = io.StringIO()
        self.stdout = io.StringIO("".join(json.dumps(line) + "\n" for line in lines))
        self.stderr = io.StringIO("")
        self.terminated = False

    def terminate(self) -> None:
        self.terminated = True

    def wait(self, timeout=None) -> int:
        return 0

    def kill(self) -> None:
        self.terminated = True


class AppServerClientTests(unittest.TestCase):
    def _make_client(self, lines):
        import sys

        sys.path.insert(0, str(ROOT))
        from server.app_server_client import CodexAppServerClient

        return CodexAppServerClient(
            popen_factory=lambda *args, **kwargs: _FakeProcess(lines),
            timeout_seconds=0.1,
        )

    def test_send_prompt_to_thread_returns_thread_and_turn(self) -> None:
        client = self._make_client(
            [
                {"id": 1, "result": {"ok": True}},
                {"method": "thread/status/changed", "params": {"threadId": "thread-1", "status": {"type": "idle"}}},
                {"id": 2, "result": {"thread": {"id": "thread-1", "name": "Helm2"}}},
                {"id": 3, "result": {"turn": {"id": "turn-1", "status": "inProgress"}}},
            ]
        )

        result = client.send_prompt_to_thread(thread_id="thread-1", message="continue")

        self.assertEqual(result["thread"]["id"], "thread-1")
        self.assertEqual(result["turn"]["id"], "turn-1")

    def test_raises_on_error_response(self) -> None:
        client = self._make_client(
            [
                {"id": 1, "result": {"ok": True}},
                {"id": 2, "error": {"message": "thread not found"}},
            ]
        )

        with self.assertRaises(RuntimeError):
            client.send_prompt_to_thread(thread_id="missing", message="continue")


if __name__ == "__main__":
    unittest.main()
