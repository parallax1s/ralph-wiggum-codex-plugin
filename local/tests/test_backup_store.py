import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BackupStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.backups_path = Path(self.tempdir.name) / "thread-backups.json"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_saves_and_loads_latest_backup_for_thread(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT))
        from server.backup_store import BackupStore

        store = BackupStore(self.backups_path)
        store.save_backup(
            thread_id="thread-old",
            operation="move_thread_to_workspace",
            target_cwd="/Users/mo/Desktop/Prj.nosync/Helm",
            row_data={
                "id": "thread-old",
                "cwd": "/tmp/project-b",
                "git_branch": "core-feature",
                "git_sha": "sha-old",
                "git_origin_url": "git@example.com:old.git",
            },
        )

        latest = store.load_latest_backup("thread-old")

        self.assertIsNotNone(latest)
        self.assertEqual(latest.thread_id, "thread-old")
        self.assertEqual(latest.target_cwd, "/Users/mo/Desktop/Prj.nosync/Helm")
        self.assertEqual(latest.row_data["cwd"], "/tmp/project-b")


if __name__ == "__main__":
    unittest.main()
