from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ThreadRecord:
    id: str
    title: str
    cwd: str
    rollout_path: str
    archived: bool
    created_at: int
    updated_at: int
    source: str
    model_provider: str
    git_sha: str | None = None
    git_branch: str | None = None
    git_origin_url: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def metadata_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "cwd": self.cwd,
            "rollout_path": self.rollout_path,
            "archived": self.archived,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source": self.source,
            "model_provider": self.model_provider,
            "git_sha": self.git_sha,
            "git_branch": self.git_branch,
            "git_origin_url": self.git_origin_url,
        }


@dataclass(frozen=True)
class ThreadMovePreview:
    thread_id: str
    before: dict[str, object]
    after: dict[str, object]
    changed_fields: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ThreadBackupRecord:
    thread_id: str
    operation: str
    target_cwd: str
    created_at: str
    row_data: dict[str, object]
    rollout_path: str | None = None
    rollout_backup_path: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RestartPlan:
    quit_command: list[str]
    launch_command: list[str]
    sleep_seconds: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RestartResult:
    plan: RestartPlan
    executed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "executed": self.executed,
            "plan": self.plan.to_dict(),
        }
