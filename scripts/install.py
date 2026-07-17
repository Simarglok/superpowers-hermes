#!/usr/bin/env python3
"""Install or roll back the Superpowers Hermes skill pack safely."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
CATEGORY = "software-development"
NEW_SKILLS = (
    "brainstorming",
    "dispatching-parallel-agents",
    "executing-plans",
    "finishing-a-development-branch",
    "receiving-code-review",
    "subagent-driven-development",
    "using-git-worktrees",
    "verification-before-completion",
)
OVERLAY_SKILLS = (
    "requesting-code-review",
    "systematic-debugging",
    "test-driven-development",
    "plan",
    "hermes-agent-skill-authoring",
)


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update((path.stat().st_mode & 0o777).to_bytes(2, "big"))
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def copy_directory(source: Path, destination: Path) -> None:
    temporary = destination.with_name(destination.name + ".superpowers-hermes-tmp")
    if temporary.exists():
        shutil.rmtree(temporary)
    shutil.copytree(source, temporary, copy_function=shutil.copy2)
    if destination.exists():
        shutil.rmtree(destination)
    temporary.replace(destination)


def install(dest: Path, state_path: Path, backup_root: Path) -> None:
    if state_path.exists():
        raise RuntimeError(f"installation state already exists: {state_path}; roll back first")

    category = dest / CATEGORY
    new_sources = {name: PACK_ROOT / "skills" / CATEGORY / name for name in NEW_SKILLS}
    overlay_sources = {
        name: PACK_ROOT / "overlays" / CATEGORY / name for name in OVERLAY_SKILLS
    }
    for source in (*new_sources.values(), *overlay_sources.values()):
        if not (source / "SKILL.md").is_file():
            raise RuntimeError(f"invalid pack source: {source}")

    conflicts = [name for name in NEW_SKILLS if (category / name).exists()]
    if conflicts:
        raise RuntimeError(
            "refusing to overwrite existing new-skill targets: " + ", ".join(conflicts)
        )

    install_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup_dir = backup_root / install_id
    overlay_backups: dict[str, str | None] = {}

    category.mkdir(parents=True, exist_ok=True)
    for name in OVERLAY_SKILLS:
        target = category / name
        if target.exists():
            backup = backup_dir / CATEGORY / name
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(target, backup, copy_function=shutil.copy2)
            overlay_backups[name] = str(backup)
        else:
            overlay_backups[name] = None

    installed_hashes: dict[str, str] = {}
    try:
        for name, source in new_sources.items():
            target = category / name
            copy_directory(source, target)
            installed_hashes[name] = tree_hash(target)
        for name, source in overlay_sources.items():
            target = category / name
            copy_directory(source, target)
            installed_hashes[name] = tree_hash(target)
    except Exception:
        for name in NEW_SKILLS:
            shutil.rmtree(category / name, ignore_errors=True)
        for name in OVERLAY_SKILLS:
            target = category / name
            shutil.rmtree(target, ignore_errors=True)
            backup = overlay_backups.get(name)
            if backup:
                shutil.copytree(Path(backup), target, copy_function=shutil.copy2)
        raise

    state = {
        "schema_version": 1,
        "pack_root": str(PACK_ROOT),
        "source": json.loads((PACK_ROOT / "SOURCE.json").read_text()),
        "installed_at": install_id,
        "dest": str(dest),
        "backup_dir": str(backup_dir),
        "new_skills": list(NEW_SKILLS),
        "overlays": list(OVERLAY_SKILLS),
        "overlay_backups": overlay_backups,
        "installed_hashes": installed_hashes,
    }
    atomic_json(state_path, state)
    print(f"installed {len(NEW_SKILLS)} new skills and {len(OVERLAY_SKILLS)} overlays")
    print(f"state: {state_path}")
    print("start a fresh Hermes session (or reload skills) before testing discovery")


def rollback(dest: Path, state_path: Path, force: bool) -> None:
    if not state_path.is_file():
        raise RuntimeError(f"installation state not found: {state_path}")
    state = json.loads(state_path.read_text())
    if Path(state["dest"]).resolve() != dest.resolve():
        raise RuntimeError("state destination does not match --dest")

    category = dest / CATEGORY
    changed: list[str] = []
    for name, expected in state["installed_hashes"].items():
        target = category / name
        if not target.exists() or tree_hash(target) != expected:
            changed.append(name)
    if changed and not force:
        raise RuntimeError(
            "installed skills changed since install; refusing rollback without --force: "
            + ", ".join(sorted(changed))
        )

    for name in state["new_skills"]:
        shutil.rmtree(category / name, ignore_errors=True)
    for name in state["overlays"]:
        target = category / name
        shutil.rmtree(target, ignore_errors=True)
        backup = state["overlay_backups"].get(name)
        if backup:
            shutil.copytree(Path(backup), target, copy_function=shutil.copy2)

    state_path.unlink()
    print(f"rolled back installation from {state['installed_at']}")


def parser() -> argparse.ArgumentParser:
    default_dest = Path.home() / ".hermes" / "skills"
    default_state = Path.home() / ".hermes" / "superpowers-hermes-install.json"
    default_backups = Path.home() / ".hermes" / "backups" / "superpowers-hermes"
    result = argparse.ArgumentParser(description=__doc__)
    subparsers = result.add_subparsers(dest="command", required=True)
    for command in ("install", "rollback"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--dest", type=Path, default=default_dest)
        sub.add_argument("--state", type=Path, default=default_state)
        if command == "install":
            sub.add_argument("--backup-root", type=Path, default=default_backups)
        else:
            sub.add_argument("--force", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "install":
            install(args.dest, args.state, args.backup_root)
        else:
            rollback(args.dest, args.state, args.force)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
