from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from .backup_store import BackupStore
from .models import ThreadMovePreview, ThreadRecord


class ThreadStore:
    def __init__(self, db_path: Path, backup_store: BackupStore | None = None) -> None:
        self.db_path = Path(db_path)
        self.backup_store = backup_store

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def list_threads(self, limit: int = 20, include_archived: bool = False) -> list[ThreadRecord]:
        query = """
            SELECT
                id,
                title,
                cwd,
                rollout_path,
                archived,
                created_at,
                updated_at,
                source,
                model_provider,
                git_sha,
                git_branch,
                git_origin_url
            FROM threads
        """
        params: list[object] = []
        if not include_archived:
            query += " WHERE archived = 0"
        query += " ORDER BY updated_at DESC, created_at DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    def get_thread(
        self,
        *,
        thread_id: str | None = None,
        title: str | None = None,
        include_archived: bool = True,
    ) -> ThreadRecord | None:
        if not thread_id and not title:
            raise ValueError("thread_id or title is required")

        query = """
            SELECT
                id,
                title,
                cwd,
                rollout_path,
                archived,
                created_at,
                updated_at,
                source,
                model_provider,
                git_sha,
                git_branch,
                git_origin_url
            FROM threads
        """
        clauses: list[str] = []
        params: list[object] = []

        if thread_id:
            clauses.append("id = ?")
            params.append(thread_id)
        elif title:
            clauses.append("title = ?")
            params.append(title)

        if not include_archived:
            clauses.append("archived = 0")

        query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY updated_at DESC LIMIT 1"

        with self._connect() as conn:
            row = conn.execute(query, params).fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def preview_move(
        self,
        *,
        thread_id: str,
        target_cwd: str,
        mode: str,
        git_branch: str | None = None,
        git_sha: str | None = None,
        git_origin_url: str | None = None,
    ) -> ThreadMovePreview:
        thread = self.get_thread(thread_id=thread_id)
        if thread is None:
            raise RuntimeError(f"Thread not found: {thread_id}")
        before = thread.metadata_dict()
        after = dict(before)
        after["cwd"] = target_cwd
        if mode == "full_metadata":
            if git_branch is not None:
                after["git_branch"] = git_branch
            if git_sha is not None:
                after["git_sha"] = git_sha
            if git_origin_url is not None:
                after["git_origin_url"] = git_origin_url
        elif mode != "cwd_only":
            raise RuntimeError(f"Unsupported move mode: {mode}")

        changed_fields = [
            key
            for key in after
            if before.get(key) != after.get(key)
        ]
        return ThreadMovePreview(
            thread_id=thread.id,
            before=before,
            after=after,
            changed_fields=changed_fields,
        )

    def move_thread(
        self,
        *,
        thread_id: str,
        target_cwd: str,
        mode: str,
        deep_move: bool = False,
        git_branch: str | None = None,
        git_sha: str | None = None,
        git_origin_url: str | None = None,
    ) -> ThreadRecord:
        preview = self.preview_move(
            thread_id=thread_id,
            target_cwd=target_cwd,
            mode=mode,
            git_branch=git_branch,
            git_sha=git_sha,
            git_origin_url=git_origin_url,
        )
        if self.backup_store is not None:
            self.backup_store.save_backup(
                thread_id=thread_id,
                operation="move_thread_to_workspace",
                target_cwd=target_cwd,
                row_data=preview.before,
                rollout_path=str(preview.before["rollout_path"]) if deep_move else None,
            )

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE threads
                SET cwd = ?, git_branch = ?, git_sha = ?, git_origin_url = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    preview.after["cwd"],
                    preview.after["git_branch"],
                    preview.after["git_sha"],
                    preview.after["git_origin_url"],
                    int(time.time()),
                    thread_id,
                ),
            )
            conn.commit()
        if deep_move:
            self._patch_rollout_session_meta_cwd(
                rollout_path=Path(str(preview.after["rollout_path"])),
                target_cwd=target_cwd,
            )
        moved = self.get_thread(thread_id=thread_id)
        if moved is None:
            raise RuntimeError(f"Thread disappeared after move: {thread_id}")
        return moved

    def undo_last_move(self, thread_id: str) -> ThreadRecord:
        if self.backup_store is None:
            raise RuntimeError("Backup store is required for undo")
        backup = self.backup_store.load_latest_backup(thread_id)
        if backup is None:
            raise RuntimeError(f"No backup found for thread: {thread_id}")
        row_data = backup.row_data
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE threads
                SET cwd = ?, git_branch = ?, git_sha = ?, git_origin_url = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    row_data.get("cwd"),
                    row_data.get("git_branch"),
                    row_data.get("git_sha"),
                    row_data.get("git_origin_url"),
                    int(time.time()),
                    thread_id,
                ),
            )
            conn.commit()
        self.backup_store.restore_rollout_backup(backup)
        restored = self.get_thread(thread_id=thread_id)
        if restored is None:
            raise RuntimeError(f"Thread disappeared after undo: {thread_id}")
        return restored

    def fork_thread(self, *, thread_id: str, target_cwd: str) -> ThreadRecord:
        raise RuntimeError("fork_thread_to_workspace is not supported yet")

    def _patch_rollout_session_meta_cwd(self, *, rollout_path: Path, target_cwd: str) -> None:
        lines = rollout_path.read_text(encoding="utf-8").splitlines()
        if not lines:
            raise RuntimeError(f"Rollout file is empty: {rollout_path}")
        try:
            first = json.loads(lines[0])
        except json.JSONDecodeError as error:
            raise RuntimeError(f"Failed to parse rollout session_meta: {rollout_path}") from error

        if first.get("type") != "session_meta":
            raise RuntimeError(f"First rollout item is not session_meta: {rollout_path}")
        payload = first.get("payload")
        if not isinstance(payload, dict) or "cwd" not in payload:
            raise RuntimeError(f"Rollout session_meta payload.cwd missing: {rollout_path}")

        payload["cwd"] = target_cwd
        first["payload"] = payload
        lines[0] = json.dumps(first, separators=(",", ":"))
        rollout_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def _row_to_record(row: tuple[object, ...]) -> ThreadRecord:
        return ThreadRecord(
            id=str(row[0]),
            title=str(row[1]),
            cwd=str(row[2]),
            rollout_path=str(row[3]),
            archived=bool(row[4]),
            created_at=int(row[5]),
            updated_at=int(row[6]),
            source=str(row[7]),
            model_provider=str(row[8]),
            git_sha=str(row[9]) if row[9] is not None else None,
            git_branch=str(row[10]) if row[10] is not None else None,
            git_origin_url=str(row[11]) if row[11] is not None else None,
        )
