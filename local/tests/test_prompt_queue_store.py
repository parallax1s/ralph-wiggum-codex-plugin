import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PromptQueueStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.queue_path = Path(self.tempdir.name) / "prompt-queue.json"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _make_store(self):
        import sys

        sys.path.insert(0, str(ROOT))
        from server.prompt_queue_store import PromptQueueStore

        return PromptQueueStore(self.queue_path)

    def test_queue_and_peek_prompt(self) -> None:
        store = self._make_store()
        store.queue_prompt(thread_id="thread-1", message="continue", title="Thread One")

        queued = store.peek_prompt("thread-1")

        self.assertIsNotNone(queued)
        self.assertEqual(queued["message"], "continue")
        self.assertEqual(queued["title"], "Thread One")

    def test_consume_prompt_returns_once_and_clears(self) -> None:
        store = self._make_store()
        store.queue_prompt(thread_id="thread-1", message="go on")

        first = store.consume_prompt("thread-1")
        second = store.consume_prompt("thread-1")

        self.assertIsNotNone(first)
        self.assertEqual(first["message"], "go on")
        self.assertIsNone(second)

    def test_consume_by_rollout_path_returns_once_and_clears(self) -> None:
        store = self._make_store()
        store.queue_prompt(thread_id="thread-1", message="continue", rollout_path="/tmp/thread.jsonl")

        first = store.consume_by_rollout_path("/tmp/thread.jsonl")
        second = store.consume_by_rollout_path("/tmp/thread.jsonl")

        self.assertIsNotNone(first)
        self.assertEqual(first["message"], "continue")
        self.assertIsNone(second)

    def test_clear_prompt_reports_whether_anything_was_removed(self) -> None:
        store = self._make_store()
        store.queue_prompt(thread_id="thread-1", message="continue")

        self.assertTrue(store.clear_prompt("thread-1"))
        self.assertFalse(store.clear_prompt("thread-1"))


if __name__ == "__main__":
    unittest.main()
