from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


EXPERIMENTAL_RESUME_RE = re.compile(r"^experimental_resume\s*=\s*.*$\n?", re.MULTILINE)


class ConfigStore:
    def __init__(self, config_path: Path) -> None:
        self.config_path = Path(config_path)

    def set_experimental_resume(self, rollout_path: str) -> Path:
        backup_path = self._backup()
        text = self._read_text()
        line = f'experimental_resume = "{rollout_path}"\n'

        if EXPERIMENTAL_RESUME_RE.search(text):
            updated = EXPERIMENTAL_RESUME_RE.sub(line, text, count=1)
        else:
            if text and not text.endswith("\n"):
                text += "\n"
            updated = text + ("\n" if text else "") + line
        self.config_path.write_text(updated, encoding="utf-8")
        return backup_path

    def clear_experimental_resume(self) -> Path:
        backup_path = self._backup()
        text = self._read_text()
        updated = EXPERIMENTAL_RESUME_RE.sub("", text)
        updated = re.sub(r"\n{3,}", "\n\n", updated)
        self.config_path.write_text(updated, encoding="utf-8")
        return backup_path

    def _read_text(self) -> str:
        if not self.config_path.exists():
            return ""
        return self.config_path.read_text(encoding="utf-8")

    def _backup(self) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        backup_path = self.config_path.with_name(f"{self.config_path.name}.bak.{timestamp}")
        if self.config_path.exists():
            shutil.copy2(self.config_path, backup_path)
        else:
            backup_path.write_text("", encoding="utf-8")
        return backup_path
