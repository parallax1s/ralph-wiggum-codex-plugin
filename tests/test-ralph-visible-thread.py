import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ralph-visible-thread.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("ralph_visible_thread", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RalphVisibleThreadTests(unittest.TestCase):
    def test_extract_turn_id_accepts_id_and_turnid(self) -> None:
        module = _load_module()
        self.assertEqual(module._extract_turn_id({"turn": {"id": "turn-1"}}), "turn-1")
        self.assertEqual(module._extract_turn_id({"turn": {"turnId": "turn-2"}}), "turn-2")
        self.assertEqual(module._extract_turn_id({"id": "turn-3"}), "turn-3")
        self.assertIsNone(module._extract_turn_id({}))

    def test_start_turn_with_retry_waits_when_thread_is_busy(self) -> None:
        module = _load_module()

        class FakeClient:
            def __init__(self):
                self.start_calls = 0
                self.wait_calls = 0

            def start_turn(self, *, conversation_id: str, message: str):
                self.start_calls += 1
                if self.start_calls == 1:
                    raise RuntimeError("conversation already has in-progress turn(s): turn-busy")
                return {"turn": {"id": "turn-2", "status": "inProgress"}}

            def wait_for_latest_turn_settled(self, *, conversation_id: str, quiet_seconds: float):
                self.wait_calls += 1
                return {"outcome": "settled", "turn": {"turnId": "turn-busy", "status": "completed"}}

        fake = FakeClient()
        result = module._start_turn_with_retry(
            fake,
            thread_id="thread-1",
            message="continue",
            timeout_seconds=5.0,
        )

        self.assertEqual(result["turn"]["id"], "turn-2")
        self.assertEqual(fake.start_calls, 2)
        self.assertEqual(fake.wait_calls, 1)


if __name__ == "__main__":
    unittest.main()
