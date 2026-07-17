# Superpowers for Hermes Agent

Hermes-native port of the behavior and workflows from [obra/superpowers](https://github.com/obra/superpowers), pinned to upstream 6.1.1.

This pack accounts for all 14 upstream skills without installing conflicting duplicates:

- 8 new Hermes-native skills under `skills/software-development/`;
- 5 controlled overlays for existing canonical Hermes skills;
- `using-superpowers` represented by Hermes runtime policy plus [`references/hermes-agent-tools.md`](references/hermes-agent-tools.md).

See `migration-manifest.yaml`, `SOURCE.json`, and `SOURCE-FILES.json` for the exact mapping and provenance.

## Safety model

The installer:

1. refuses to overwrite any of the eight new-skill target names;
2. backs up every existing canonical overlay;
3. installs complete directories atomically;
4. records hashes and backup locations in an installation-state file;
5. refuses rollback if installed files changed, unless `--force` is explicitly supplied.

It does not edit Hermes configuration and does not commit, push, merge, or modify the upstream checkout.

## Validate the pack

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
bash -n skills/software-development/brainstorming/scripts/*.sh
node --check skills/software-development/brainstorming/scripts/server.cjs
node --check skills/software-development/brainstorming/scripts/helper.js
```

## Install into the default profile

Review the complete diff first, then run:

```bash
python3 scripts/install.py install
```

Defaults:

- skills: `~/.hermes/skills/`;
- state: `~/.hermes/superpowers-hermes-install.json`;
- backups: `~/.hermes/backups/superpowers-hermes/<timestamp>/`.

Use `--dest`, `--state`, and `--backup-root` for an isolated test profile. Start a fresh Hermes session or reload skills after installation.

## Roll back

```bash
python3 scripts/install.py rollback
```

Rollback removes the eight newly installed skills and restores the five canonical directories from backup. If any installed directory changed after installation, rollback stops rather than deleting those edits. Inspect the changes before using `--force`.

## Update

1. Pin the new upstream commit in `SOURCE.json`.
2. Regenerate `SOURCE-FILES.json` and the archive tree hash.
3. Review upstream changes skill-by-skill.
4. Update `migration-manifest.yaml`, new skills, and overlays deliberately.
5. Run static and isolated installer tests.
6. Run fresh-session behavioral acceptance tests.
7. Roll back the active version, then install the validated update.

Do not point Hermes directly at a mutable upstream checkout. Local precedence and duplicate names would silently mix methodologies.

## Required acceptance prompt

In a fresh Hermes session, send exactly:

> Let's make a react todo list

Passing behavior:

- `brainstorming` loads before code, scaffolding, or mutating commands;
- the agent asks about intent and constraints;
- it presents alternatives and waits for design approval;
- implementation does not begin before approval and planning.

## Scope

The Visual Companion assets are included, but browser/server behavior remains optional. Text-only brainstorming is always valid. Starting the companion requires explicit user opt-in and Hermes-managed background-process lifecycle.

## License

The upstream work is MIT licensed. Attribution and pinned source information are preserved in this repository.
