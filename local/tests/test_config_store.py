import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ConfigStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.tempdir.name) / "config.toml"
        self.config_path.write_text(
            'model = "gpt-5.4"\n'
            "[features]\n"
            "skills = true\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_sets_experimental_resume_and_creates_backup(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT))
        from server.config_store import ConfigStore

        store = ConfigStore(self.config_path)
        backup_path = store.set_experimental_resume("/tmp/thread.jsonl")

        text = self.config_path.read_text(encoding="utf-8")
        self.assertIn('experimental_resume = "/tmp/thread.jsonl"', text)
        self.assertTrue(backup_path.exists())

    def test_replaces_existing_experimental_resume(self) -> None:
        import sys

        self.config_path.write_text(
            'model = "gpt-5.4"\n'
            'experimental_resume = "/tmp/old.jsonl"\n',
            encoding="utf-8",
        )
        sys.path.insert(0, str(ROOT))
        from server.config_store import ConfigStore

        store = ConfigStore(self.config_path)
        store.set_experimental_resume("/tmp/new.jsonl")

        text = self.config_path.read_text(encoding="utf-8")
        self.assertIn('experimental_resume = "/tmp/new.jsonl"', text)
        self.assertNotIn('experimental_resume = "/tmp/old.jsonl"', text)

    def test_clear_experimental_resume_removes_line(self) -> None:
        import sys

        self.config_path.write_text(
            'model = "gpt-5.4"\n'
            'experimental_resume = "/tmp/old.jsonl"\n'
            "[features]\n"
            "skills = true\n",
            encoding="utf-8",
        )
        sys.path.insert(0, str(ROOT))
        from server.config_store import ConfigStore

        store = ConfigStore(self.config_path)
        store.clear_experimental_resume()

        text = self.config_path.read_text(encoding="utf-8")
        self.assertNotIn("experimental_resume", text)
        self.assertIn("[features]", text)


if __name__ == "__main__":
    unittest.main()
