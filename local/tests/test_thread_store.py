import sqlite3
import tempfile
import unittest
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ThreadStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "state.sqlite"
        self.backups_path = Path(self.tempdir.name) / "thread-backups.json"
        self.rollout_dir = Path(self.tempdir.name) / "rollouts"
        self.rollout_dir.mkdir(parents=True, exist_ok=True)
        self._build_fixture(self.db_path)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _build_fixture(self, db_path: Path) -> None:
        rollout_new = self.rollout_dir / "thread-new.jsonl"
        rollout_old = self.rollout_dir / "thread-old.jsonl"
        rollout_archived = self.rollout_dir / "thread-archived.jsonl"
        self._write_rollout(rollout_new, "/tmp/project-a")
        self._write_rollout(rollout_old, "/tmp/project-b")
        self._write_rollout(rollout_archived, "/tmp/project-c")
        conn = sqlite3.connect(db_path)
        conn.executescript(
            """
            CREATE TABLE threads (
                id TEXT PRIMARY KEY,
                rollout_path TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                source TEXT NOT NULL,
                model_provider TEXT NOT NULL,
                cwd TEXT NOT NULL,
                title TEXT NOT NULL,
                sandbox_policy TEXT NOT NULL,
                approval_mode TEXT NOT NULL,
                tokens_used INTEGER NOT NULL DEFAULT 0,
                has_user_event INTEGER NOT NULL DEFAULT 0,
                archived INTEGER NOT NULL DEFAULT 0,
                archived_at INTEGER,
                git_sha TEXT,
                git_branch TEXT,
                git_origin_url TEXT,
                cli_version TEXT NOT NULL DEFAULT '',
                first_user_message TEXT NOT NULL DEFAULT '',
                agent_nickname TEXT,
                agent_role TEXT,
                memory_mode TEXT NOT NULL DEFAULT 'enabled',
                model TEXT,
                reasoning_effort TEXT,
                agent_path TEXT
            );
            """
        )
        conn.executemany(
            """
            INSERT INTO threads (
                id, rollout_path, created_at, updated_at, source, model_provider, cwd, title,
                sandbox_policy, approval_mode, archived, git_sha, git_branch, git_origin_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "thread-new",
                    str(rollout_new),
                    10,
                    50,
                    "desktop",
                    "openai",
                    "/tmp/project-a",
                    "Newest Thread",
                    "danger-full-access",
                    "never",
                    0,
                    "sha-new",
                    "core-main",
                    "git@example.com:core.git",
                ),
                (
                    "thread-old",
                    str(rollout_old),
                    5,
                    20,
                    "desktop",
                    "openai",
                    "/tmp/project-b",
                    "Older Thread",
                    "danger-full-access",
                    "never",
                    0,
                    "sha-old",
                    "core-feature",
                    "git@example.com:old.git",
                ),
                (
                    "thread-archived",
                    str(rollout_archived),
                    1,
                    100,
                    "desktop",
                    "openai",
                    "/tmp/project-c",
                    "Archived Thread",
                    "danger-full-access",
                    "never",
                    1,
                    "sha-archived",
                    "core-archived",
                    "git@example.com:archived.git",
                ),
            ],
        )
        conn.commit()
        conn.close()

    def _write_rollout(self, path: Path, cwd: str) -> None:
        first = {
            "timestamp": "2026-04-03T15:11:56.237Z",
            "type": "session_meta",
            "payload": {
                "id": path.stem,
                "cwd": cwd,
                "source": "desktop",
            },
        }
        second = {
            "timestamp": "2026-04-03T15:12:00.000Z",
            "type": "event_msg",
            "payload": {
                "message": f"workspace {cwd}",
            },
        }
        path.write_text(
            "\n".join(
                [
                    json.dumps(first, separators=(",", ":")),
                    json.dumps(second, separators=(",", ":")),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    def _make_store(self):
        import sys

        sys.path.insert(0, str(ROOT))
        from server.backup_store import BackupStore
        from server.thread_store import ThreadStore

        return ThreadStore(
            self.db_path,
            backup_store=BackupStore(self.backups_path),
        )

    def test_lists_recent_non_archived_threads_first(self) -> None:
        store = self._make_store()
        threads = store.list_threads(limit=10)

        self.assertEqual([thread.id for thread in threads], ["thread-new", "thread-old"])

    def test_can_include_archived_threads(self) -> None:
        store = self._make_store()
        threads = store.list_threads(limit=10, include_archived=True)

        self.assertEqual(threads[0].id, "thread-archived")
        self.assertEqual(len(threads), 3)

    def test_finds_thread_by_id(self) -> None:
        store = self._make_store()
        thread = store.get_thread(thread_id="thread-old")

        self.assertIsNotNone(thread)
        self.assertEqual(thread.title, "Older Thread")

    def test_finds_thread_by_exact_title(self) -> None:
        store = self._make_store()
        thread = store.get_thread(title="Newest Thread")

        self.assertIsNotNone(thread)
        self.assertEqual(thread.id, "thread-new")

    def test_returns_none_for_missing_thread(self) -> None:
        store = self._make_store()

        self.assertIsNone(store.get_thread(thread_id="missing"))

    def test_previews_cwd_only_move(self) -> None:
        store = self._make_store()

        preview = store.preview_move(
            thread_id="thread-old",
            target_cwd="/Users/mo/Desktop/Prj.nosync/Helm",
            mode="cwd_only",
        )

        self.assertEqual(preview.thread_id, "thread-old")
        self.assertEqual(preview.before["cwd"], "/tmp/project-b")
        self.assertEqual(preview.after["cwd"], "/Users/mo/Desktop/Prj.nosync/Helm")
        self.assertEqual(preview.changed_fields, ["cwd"])

    def test_moves_thread_with_cwd_only_mode(self) -> None:
        store = self._make_store()

        moved = store.move_thread(
            thread_id="thread-old",
            target_cwd="/Users/mo/Desktop/Prj.nosync/Helm",
            mode="cwd_only",
        )

        self.assertEqual(moved.cwd, "/Users/mo/Desktop/Prj.nosync/Helm")
        self.assertEqual(moved.git_branch, "core-feature")
        self.assertEqual(moved.git_sha, "sha-old")
        rollout_text = Path(moved.rollout_path).read_text(encoding="utf-8")
        self.assertIn('"cwd":"/tmp/project-b"', rollout_text)

    def test_moves_thread_with_full_metadata_mode(self) -> None:
        store = self._make_store()

        moved = store.move_thread(
            thread_id="thread-old",
            target_cwd="/Users/mo/Desktop/Prj.nosync/Helm",
            mode="full_metadata",
            git_branch="helm-main",
            git_sha="helm-sha",
            git_origin_url="git@example.com:helm.git",
        )

        self.assertEqual(moved.cwd, "/Users/mo/Desktop/Prj.nosync/Helm")
        self.assertEqual(moved.git_branch, "helm-main")
        self.assertEqual(moved.git_sha, "helm-sha")
        self.assertEqual(moved.git_origin_url, "git@example.com:helm.git")

    def test_deep_move_patches_only_first_session_meta_cwd(self) -> None:
        store = self._make_store()

        moved = store.move_thread(
            thread_id="thread-old",
            target_cwd="/Users/mo/Desktop/Prj.nosync/Helm",
            mode="full_metadata",
            deep_move=True,
            git_branch="helm-main",
            git_sha="helm-sha",
            git_origin_url="git@example.com:helm.git",
        )

        rollout_text = Path(moved.rollout_path).read_text(encoding="utf-8")
        self.assertIn('"cwd":"/Users/mo/Desktop/Prj.nosync/Helm"', rollout_text.splitlines()[0])
        self.assertIn('workspace /tmp/project-b', rollout_text)

    def test_undo_restores_previous_thread_metadata(self) -> None:
        store = self._make_store()
        store.move_thread(
            thread_id="thread-old",
            target_cwd="/Users/mo/Desktop/Prj.nosync/Helm",
            mode="full_metadata",
            git_branch="helm-main",
            git_sha="helm-sha",
            git_origin_url="git@example.com:helm.git",
        )

        restored = store.undo_last_move("thread-old")

        self.assertEqual(restored.cwd, "/tmp/project-b")
        self.assertEqual(restored.git_branch, "core-feature")
        self.assertEqual(restored.git_sha, "sha-old")
        self.assertEqual(restored.git_origin_url, "git@example.com:old.git")

    def test_undo_restores_rollout_session_meta_after_deep_move(self) -> None:
        store = self._make_store()
        moved = store.move_thread(
            thread_id="thread-old",
            target_cwd="/Users/mo/Desktop/Prj.nosync/Helm",
            mode="full_metadata",
            deep_move=True,
            git_branch="helm-main",
            git_sha="helm-sha",
            git_origin_url="git@example.com:helm.git",
        )
        self.assertIn(
            '"cwd":"/Users/mo/Desktop/Prj.nosync/Helm"',
            Path(moved.rollout_path).read_text(encoding="utf-8").splitlines()[0],
        )

        restored = store.undo_last_move("thread-old")

        self.assertIn(
            '"cwd":"/tmp/project-b"',
            Path(restored.rollout_path).read_text(encoding="utf-8").splitlines()[0],
        )

    def test_fork_is_rejected_until_supported_safely(self) -> None:
        store = self._make_store()

        with self.assertRaisesRegex(RuntimeError, "not supported yet"):
            store.fork_thread(
                thread_id="thread-old",
                target_cwd="/Users/mo/Desktop/Prj.nosync/Helm",
            )


if __name__ == "__main__":
    unittest.main()
