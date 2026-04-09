import importlib.util
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ralph-arm-visible-thread.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("ralph_arm_visible_thread", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class AwaitLaunchableSettleTests(unittest.TestCase):
    def test_retries_on_superseded_until_settled(self) -> None:
        module = _load_module()

        class FakeClient:
            def __init__(self):
                self.calls = 0

            def wait_for_latest_turn_settled(self, *, conversation_id: str, quiet_seconds: float):
                self.calls += 1
                if self.calls == 1:
                    return {
                        "outcome": "superseded",
                        "supersedingTurn": {"turnId": "turn-2"},
                    }
                return {"outcome": "settled", "turn": {"turnId": "turn-2", "status": "completed"}}

        fake = FakeClient()
        stderr = io.StringIO()
        with patch.object(sys, "stderr", stderr):
            result = module._await_launchable_settle(fake, thread_id="thread-1", quiet_seconds=2.0)

        self.assertEqual(result["outcome"], "settled")
        self.assertEqual(fake.calls, 2)
        self.assertIn("superseded by newer turn turn-2; continuing to watch", stderr.getvalue())

    def test_returns_immediately_when_already_settled(self) -> None:
        module = _load_module()

        class FakeClient:
            def wait_for_latest_turn_settled(self, *, conversation_id: str, quiet_seconds: float):
                return {"outcome": "settled", "turn": {"turnId": "turn-1", "status": "completed"}}

        result = module._await_launchable_settle(FakeClient(), thread_id="thread-1", quiet_seconds=2.0)
        self.assertEqual(result["turn"]["turnId"], "turn-1")


if __name__ == "__main__":
    unittest.main()
