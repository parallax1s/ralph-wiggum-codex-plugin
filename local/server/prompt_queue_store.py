from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class PromptQueueStore:
    def __init__(self, queue_path: Path) -> None:
        self.queue_path = Path(queue_path)

    def queue_prompt(self, *, thread_id: str, message: str, title: str | None = None) -> dict[str, object]:
        payload = self._read_payload()
        record = {
            "thread_id": thread_id,
            "message": message,
            "title": title,
            "queued_at": datetime.now(timezone.utc).isoformat(),
        }
        payload[thread_id] = record
        self._write_payload(payload)
        return record

    def peek_prompt(self, thread_id: str) -> dict[str, object] | None:
        return self._read_payload().get(thread_id)

    def consume_prompt(self, thread_id: str) -> dict[str, object] | None:
        payload = self._read_payload()
        record = payload.pop(thread_id, None)
        if record is not None:
            self._write_payload(payload)
        return record

    def clear_prompt(self, thread_id: str) -> bool:
        payload = self._read_payload()
        removed = thread_id in payload
        if removed:
            payload.pop(thread_id, None)
            self._write_payload(payload)
        return removed

    def _read_payload(self) -> dict[str, dict[str, object]]:
        if not self.queue_path.exists():
            return {}
        return json.loads(self.queue_path.read_text(encoding="utf-8"))

    def _write_payload(self, payload: dict[str, dict[str, object]]) -> None:
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        self.queue_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
