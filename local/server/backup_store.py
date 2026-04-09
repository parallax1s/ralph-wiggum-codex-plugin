from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .models import ThreadBackupRecord


class BackupStore:
    def __init__(self, backup_path: Path) -> None:
        self.backup_path = Path(backup_path)

    def save_backup(
        self,
        *,
        thread_id: str,
        operation: str,
        target_cwd: str,
        row_data: dict[str, object],
        rollout_path: str | None = None,
    ) -> ThreadBackupRecord:
        rollout_backup_path = None
        if rollout_path is not None:
            rollout_backup_path = str(self._backup_rollout(Path(rollout_path), thread_id))
        record = ThreadBackupRecord(
            thread_id=thread_id,
            operation=operation,
            target_cwd=target_cwd,
            created_at=datetime.now(timezone.utc).isoformat(),
            row_data=row_data,
            rollout_path=rollout_path,
            rollout_backup_path=rollout_backup_path,
        )
        payload = self._read_payload()
        payload.setdefault("records", []).append(record.to_dict())
        self._write_payload(payload)
        return record

    def load_latest_backup(self, thread_id: str) -> ThreadBackupRecord | None:
        payload = self._read_payload()
        records = payload.get("records", [])
        for raw in reversed(records):
            if raw.get("thread_id") == thread_id:
                return ThreadBackupRecord(
                    thread_id=str(raw["thread_id"]),
                    operation=str(raw["operation"]),
                    target_cwd=str(raw["target_cwd"]),
                    created_at=str(raw["created_at"]),
                    row_data=dict(raw["row_data"]),
                    rollout_path=str(raw["rollout_path"]) if raw.get("rollout_path") is not None else None,
                    rollout_backup_path=str(raw["rollout_backup_path"])
                    if raw.get("rollout_backup_path") is not None
                    else None,
                )
        return None

    def restore_rollout_backup(self, backup: ThreadBackupRecord) -> None:
        if backup.rollout_path is None or backup.rollout_backup_path is None:
            return
        shutil.copy2(backup.rollout_backup_path, backup.rollout_path)

    def _read_payload(self) -> dict[str, object]:
        if not self.backup_path.exists():
            return {"records": []}
        return json.loads(self.backup_path.read_text(encoding="utf-8"))

    def _write_payload(self, payload: dict[str, object]) -> None:
        self.backup_path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _backup_rollout(self, rollout_path: Path, thread_id: str) -> Path:
        if not rollout_path.exists():
            raise FileNotFoundError(f"Rollout file does not exist: {rollout_path}")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        backup_dir = self.backup_path.parent / "rollout-backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        target = backup_dir / f"{thread_id}-{timestamp}.jsonl"
        shutil.copy2(rollout_path, target)
        return target
