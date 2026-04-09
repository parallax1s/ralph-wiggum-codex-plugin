import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AppControlTests(unittest.TestCase):
    def test_build_restart_plan_targets_codex_app(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT))
        from server.app_control import CodexAppController

        controller = CodexAppController(app_name="Codex")
        plan = controller.build_restart_plan()

        self.assertEqual(plan.quit_command[0], "osascript")
        self.assertEqual(plan.launch_command, ["open", "-a", "Codex"])

    def test_restart_dry_run_returns_plan_without_execution(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT))
        from server.app_control import CodexAppController

        controller = CodexAppController(app_name="Codex")
        result = controller.restart(dry_run=True)

        self.assertFalse(result.executed)
        self.assertEqual(result.plan.launch_command, ["open", "-a", "Codex"])


if __name__ == "__main__":
    unittest.main()
