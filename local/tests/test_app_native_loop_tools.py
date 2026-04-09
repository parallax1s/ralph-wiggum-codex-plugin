import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AppNativeLoopToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.tempdir.name) / "config.toml"
        self.config_path.write_text('model = "gpt-5.4"\n', encoding="utf-8")
        self.queue_path = Path(self.tempdir.name) / "prompt-queue.json"
        self.rollout_path = Path(self.tempdir.name) / "thread.jsonl"
        self.rollout_path.write_text('{"type":"session_meta","payload":{"cwd":"/tmp"}}\n', encoding="utf-8")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _imports(self):
        import sys

        sys.path.insert(0, str(ROOT))
        from server import main
        from server.config_store import ConfigStore
        from server.models import RestartPlan, RestartResult, ThreadRecord
        from server.prompt_queue_store import PromptQueueStore
        return main, ConfigStore, RestartPlan, RestartResult, ThreadRecord, PromptQueueStore

    def _thread_record(self, ThreadRecord):
        return ThreadRecord(
            id="thread-1",
            title="Thread One",
            cwd="/tmp",
            rollout_path=str(self.rollout_path),
            archived=False,
            created_at=1,
            updated_at=2,
            source="desktop",
            model_provider="openai",
        )

    def test_queue_prompt_for_thread_stores_prompt(self) -> None:
        main, ConfigStore, RestartPlan, RestartResult, ThreadRecord, PromptQueueStore = self._imports()

        class FakeThreadStore:
            def get_thread(self, **_kwargs):
                return self_owner._thread_record(ThreadRecord)

        class FakeAppController:
            def restart(self, dry_run=False):
                return RestartResult(plan=RestartPlan(["quit"], ["launch"], 1.0), executed=not dry_run)

        class FakeAppServerClient:
            def send_prompt_to_thread(self, *, thread_id: str, message: str):
                return {"thread": {"id": thread_id}, "turn": {"id": "turn-1", "status": "inProgress"}}

        class FakeLiveIpcClient:
            def start_turn(self, *, conversation_id: str, message: str):
                return {"turn": {"id": "turn-1", "status": "inProgress"}}

            def interrupt_conversation(self, *, conversation_id: str):
                return {"ok": True}

        self_owner = self
        main._make_services = lambda: (
            FakeThreadStore(),
            ConfigStore(self.config_path),
            FakeAppController(),
            PromptQueueStore(self.queue_path),
            FakeAppServerClient(),
            FakeLiveIpcClient(),
        )

        result = main._handle_tool_call("queue_prompt_for_thread", {"thread_id": "thread-1", "message": "continue"})
        text = result["content"][0]["text"]

        self.assertIn('"queued": true', text)
        self.assertIn('"message": "continue"', text)

    def test_consume_queued_prompt_returns_once(self) -> None:
        main, ConfigStore, RestartPlan, RestartResult, ThreadRecord, PromptQueueStore = self._imports()
        queue_store = PromptQueueStore(self.queue_path)
        queue_store.queue_prompt(thread_id="thread-1", message="continue", title="Thread One")

        class FakeThreadStore:
            def get_thread(self, **_kwargs):
                return self_owner._thread_record(ThreadRecord)

        class FakeAppController:
            def restart(self, dry_run=False):
                return RestartResult(plan=RestartPlan(["quit"], ["launch"], 1.0), executed=not dry_run)

        class FakeAppServerClient:
            def send_prompt_to_thread(self, *, thread_id: str, message: str):
                return {"thread": {"id": thread_id}, "turn": {"id": "turn-1", "status": "inProgress"}}

        class FakeLiveIpcClient:
            def start_turn(self, *, conversation_id: str, message: str):
                return {"turn": {"id": "turn-1", "status": "inProgress"}}

            def interrupt_conversation(self, *, conversation_id: str):
                return {"ok": True}

        self_owner = self
        main._make_services = lambda: (
            FakeThreadStore(),
            ConfigStore(self.config_path),
            FakeAppController(),
            queue_store,
            FakeAppServerClient(),
            FakeLiveIpcClient(),
        )

        first = main._handle_tool_call("consume_queued_prompt", {"thread_id": "thread-1"})["content"][0]["text"]
        second = main._handle_tool_call("consume_queued_prompt", {"thread_id": "thread-1"})["content"][0]["text"]

        self.assertIn('"consumed": true', first)
        self.assertIn('"message": "continue"', first)
        self.assertIn('"consumed": false', second)

    def test_resume_thread_with_queue_stages_prompt_and_restart(self) -> None:
        main, ConfigStore, RestartPlan, RestartResult, ThreadRecord, PromptQueueStore = self._imports()
        queue_store = PromptQueueStore(self.queue_path)

        class FakeThreadStore:
            def get_thread(self, **_kwargs):
                return self_owner._thread_record(ThreadRecord)

        class FakeAppController:
            def restart(self, dry_run=False):
                return RestartResult(plan=RestartPlan(["quit"], ["launch"], 1.0), executed=not dry_run)

        class FakeAppServerClient:
            def send_prompt_to_thread(self, *, thread_id: str, message: str):
                return {"thread": {"id": thread_id}, "turn": {"id": "turn-1", "status": "inProgress"}}

        class FakeLiveIpcClient:
            def start_turn(self, *, conversation_id: str, message: str):
                return {"turn": {"id": "turn-1", "status": "inProgress"}}

            def interrupt_conversation(self, *, conversation_id: str):
                return {"ok": True}

        self_owner = self
        main._make_services = lambda: (
            FakeThreadStore(),
            ConfigStore(self.config_path),
            FakeAppController(),
            queue_store,
            FakeAppServerClient(),
            FakeLiveIpcClient(),
        )

        result = main._handle_tool_call(
            "resume_thread_with_queue",
            {"thread_id": "thread-1", "message": "go on", "restart": True, "dry_run": True},
        )["content"][0]["text"]

        self.assertIn('"staged": true', result)
        self.assertIn('"message": "go on"', result)
        self.assertIn('"restart_requested": true', result)
        self.assertIn('experimental_resume =', self.config_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
