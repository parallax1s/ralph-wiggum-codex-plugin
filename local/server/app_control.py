from __future__ import annotations

import subprocess
import time

from .models import RestartPlan, RestartResult


class CodexAppController:
    def __init__(self, app_name: str = "Codex", sleep_seconds: float = 1.0) -> None:
        self.app_name = app_name
        self.sleep_seconds = sleep_seconds

    def build_restart_plan(self) -> RestartPlan:
        return RestartPlan(
            quit_command=[
                "osascript",
                "-e",
                f'tell application "{self.app_name}" to quit',
            ],
            launch_command=["open", "-a", self.app_name],
            sleep_seconds=self.sleep_seconds,
        )

    def restart(self, dry_run: bool = False) -> RestartResult:
        plan = self.build_restart_plan()
        if dry_run:
            return RestartResult(plan=plan, executed=False)

        subprocess.run(plan.quit_command, check=False)
        time.sleep(plan.sleep_seconds)
        subprocess.run(plan.launch_command, check=True)
        return RestartResult(plan=plan, executed=True)
