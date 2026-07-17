from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install.py"
NEW = {
    "brainstorming",
    "dispatching-parallel-agents",
    "executing-plans",
    "finishing-a-development-branch",
    "receiving-code-review",
    "subagent-driven-development",
    "using-git-worktrees",
    "verification-before-completion",
}
OVERLAYS = {
    "requesting-code-review",
    "systematic-debugging",
    "test-driven-development",
    "plan",
    "hermes-agent-skill-authoring",
}


class InstallerTests(unittest.TestCase):
    def test_install_and_rollback_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            dest = base / "skills"
            state = base / "state.json"
            backups = base / "backups"
            category = dest / "software-development"
            sentinel = "---\nname: {name}\ndescription: sentinel\n---\nold\n"
            for name in OVERLAYS:
                path = category / name / "SKILL.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(sentinel.format(name=name))

            subprocess.run(
                [
                    "python3",
                    str(INSTALLER),
                    "install",
                    "--dest",
                    str(dest),
                    "--state",
                    str(state),
                    "--backup-root",
                    str(backups),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            installed = json.loads(state.read_text())
            self.assertEqual(set(installed["new_skills"]), NEW)
            self.assertEqual(set(installed["overlays"]), OVERLAYS)
            for name in NEW | OVERLAYS:
                self.assertTrue((category / name / "SKILL.md").is_file(), name)
            self.assertNotEqual(
                (category / "plan" / "SKILL.md").read_text(),
                sentinel.format(name="plan"),
            )

            subprocess.run(
                [
                    "python3",
                    str(INSTALLER),
                    "rollback",
                    "--dest",
                    str(dest),
                    "--state",
                    str(state),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            for name in NEW:
                self.assertFalse((category / name).exists(), name)
            for name in OVERLAYS:
                self.assertEqual(
                    (category / name / "SKILL.md").read_text(),
                    sentinel.format(name=name),
                )
            self.assertFalse(state.exists())


if __name__ == "__main__":
    unittest.main()
