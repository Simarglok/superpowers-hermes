from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "migration-manifest.yaml"
SOURCE = ROOT / "SOURCE.json"

EXPECTED_UPSTREAM = {
    "brainstorming": "new",
    "dispatching-parallel-agents": "new",
    "executing-plans": "new",
    "finishing-a-development-branch": "new",
    "receiving-code-review": "new",
    "requesting-code-review": "merge",
    "subagent-driven-development": "new",
    "systematic-debugging": "merge",
    "test-driven-development": "merge",
    "using-git-worktrees": "new",
    "using-superpowers": "runtime-policy",
    "verification-before-completion": "new",
    "writing-plans": "absorbed",
    "writing-skills": "absorbed",
}

NEW_SKILLS = {name for name, strategy in EXPECTED_UPSTREAM.items() if strategy == "new"}
OVERLAY_SKILLS = {
    "requesting-code-review",
    "systematic-debugging",
    "test-driven-development",
    "plan",
    "hermes-agent-skill-authoring",
}
ALLOWED_SUPPORT_DIRS = {"references", "templates", "scripts", "assets"}
FORBIDDEN_EXECUTABLE_TERMS = {
    "TodoWrite",
    "AskUserQuestion",
    "EnterWorktree",
    "Subagent (general-purpose)",
    "superpowers:",
    "CLAUDE_PLUGIN_ROOT",
    "hookSpecificOutput",
}


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def parse_frontmatter(path: Path) -> tuple[dict[str, object], str]:
    text = path.read_text()
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        raise AssertionError(f"invalid frontmatter delimiters: {path}")
    fields: dict[str, object] = {}
    for line in match.group(1).splitlines():
        if line.startswith("  ") or not line.strip() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"')
    return fields, match.group(2)


class PackContractTests(unittest.TestCase):
    def test_manifest_accounts_for_all_upstream_skills(self) -> None:
        manifest = load_manifest()
        entries = {entry["upstream_name"]: entry for entry in manifest["skills"]}
        self.assertEqual(set(entries), set(EXPECTED_UPSTREAM))
        self.assertEqual(
            {name: entries[name]["strategy"] for name in entries},
            EXPECTED_UPSTREAM,
        )

    def test_source_is_pinned(self) -> None:
        source = json.loads(SOURCE.read_text())
        self.assertEqual(source["repository"], "https://github.com/obra/superpowers.git")
        self.assertEqual(source["version"], "6.1.1")
        self.assertEqual(
            source["commit"],
            "d884ae04edebef577e82ff7c4e143debd0bbec99",
        )
        self.assertRegex(source["tree_sha256"], r"^[0-9a-f]{64}$")

    def test_new_skill_files_are_valid_and_unique(self) -> None:
        seen: set[str] = set()
        for name in sorted(NEW_SKILLS):
            path = ROOT / "skills" / "software-development" / name / "SKILL.md"
            self.assertTrue(path.is_file(), path)
            fields, body = parse_frontmatter(path)
            self.assertEqual(fields.get("name"), name)
            self.assertTrue(str(fields.get("description", "")).startswith("Use when "))
            self.assertLessEqual(len(str(fields["description"])), 1024)
            self.assertTrue(body.strip())
            self.assertNotIn(name, seen)
            seen.add(name)

    def test_new_skill_instructions_use_hermes_vocabulary(self) -> None:
        for name in sorted(NEW_SKILLS):
            path = ROOT / "skills" / "software-development" / name / "SKILL.md"
            text = path.read_text()
            for forbidden in FORBIDDEN_EXECUTABLE_TERMS:
                self.assertNotIn(forbidden, text, f"{forbidden!r} in {path}")

    def test_support_files_live_in_progressive_disclosure_directories(self) -> None:
        skills_root = ROOT / "skills"
        for path in skills_root.rglob("*"):
            if not path.is_file() or path.name == "SKILL.md":
                continue
            relative = path.relative_to(skills_root)
            self.assertGreaterEqual(len(relative.parts), 4, relative)
            self.assertIn(relative.parts[2], ALLOWED_SUPPORT_DIRS, relative)

    def test_relative_markdown_links_resolve_inside_skill_root(self) -> None:
        link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
        for skill_md in (ROOT / "skills").rglob("SKILL.md"):
            skill_root = skill_md.parent.resolve()
            for raw in link_pattern.findall(skill_md.read_text()):
                if "://" in raw or raw.startswith("#"):
                    continue
                target = (skill_md.parent / raw.split("#", 1)[0]).resolve()
                self.assertTrue(target.is_relative_to(skill_root), (skill_md, raw))
                self.assertTrue(target.exists(), (skill_md, raw))

    def test_manifest_target_names_have_no_duplicates(self) -> None:
        entries = load_manifest()["skills"]
        active_targets = [
            entry["target_name"]
            for entry in entries
            if entry["strategy"] in {"new", "merge", "absorbed"}
        ]
        self.assertEqual(len(active_targets), len(set(active_targets)))

    def test_overlay_skill_files_are_valid(self) -> None:
        for name in sorted(OVERLAY_SKILLS):
            path = ROOT / "overlays" / "software-development" / name / "SKILL.md"
            self.assertTrue(path.is_file(), path)
            fields, body = parse_frontmatter(path)
            self.assertEqual(fields.get("name"), name)
            self.assertTrue(body.strip())

    def test_manifest_supporting_files_exist(self) -> None:
        for entry in load_manifest()["skills"]:
            support = entry.get("supporting_files", [])
            if not support:
                continue
            if entry["strategy"] == "new":
                base = ROOT / entry["target_path"]
            else:
                base = ROOT / "overlays" / "software-development" / entry["target_name"]
            for relative in support:
                self.assertTrue((base / relative).is_file(), base / relative)

    def test_runtime_scripts_are_executable(self) -> None:
        script_dirs = list((ROOT / "skills").rglob("scripts"))
        script_dirs += list((ROOT / "overlays").rglob("scripts"))
        for scripts_dir in script_dirs:
            for path in scripts_dir.iterdir():
                if path.suffix in {".js", ".cjs", ".html", ".dot", ".ts"}:
                    continue
                self.assertTrue(path.stat().st_mode & 0o111, path)


if __name__ == "__main__":
    unittest.main()
